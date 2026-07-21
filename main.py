import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import pytz
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from market import get_current_price, get_gold_candles, get_tehran_time, is_market_open
from signals import create_signal
from languages import get_text, LANGUAGES

# ============================================================
# ⚠️ رفع باگ تأخیر در ارسال خودکار TP/SL: get_current_price/get_gold_candles
# از requests (blocking) استفاده می‌کنن، پس با asyncio.to_thread در یک
# ترد جدا اجرا می‌شن تا event loop اصلی فریز نشه. اما asyncio.to_thread
# به‌طور پیش‌فرض یک ThreadPoolExecutor مشترک و سراسری داره که ظرفیتش
# محدوده (روی سرورهای کم‌هسته مثل Railway، معمولاً فقط ۵ ترد) - اگه این
# pool با ترافیک سیگنال‌گیری کاربرا پر بشه، حلقه‌ی auto_tracker (که در
# فایل جدای auto_tracker.py Executor اختصاصی خودش رو داره) اثر نمی‌گیره،
# ولی برعکسش (سیگنال‌گیری کاربرا معطل بمونه) هنوز ممکنه اتفاق بیفته اگه
# اینجا هم از pool مشترک استفاده بشه. پس این فایل هم Executor اختصاصی
# خودش رو داره - کاملاً جدا از auto_tracker - تا هیچ‌کدوم رو دیگری معطل
# نکنه.
# ============================================================
_signal_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="signal_fetch")


async def _run_in_signal_thread(func, *args, **kwargs):
    """اجرای یک تابع blocking (شبکه‌ای) در Executor اختصاصی این فایل."""
    loop = asyncio.get_running_loop()
    if kwargs:
        from functools import partial
        return await loop.run_in_executor(_signal_executor, partial(func, *args, **kwargs))
    return await loop.run_in_executor(_signal_executor, func, *args)

from database import (
    create_database,
    save_trade,
    update_result,
    get_user_trades,
    get_statistics,
    get_setting,
    update_setting,
    add_user,
    update_activity,
    get_users_count,
    get_all_users,
    delete_user,
    reset_daily_signals,
    get_user_signals_left,
    use_signal,
    get_user_lang,
    get_user_style,
    get_referral_link,
    process_referral,
    get_today_stats,
    connect,
    set_user_rr,
    get_user_rr,
    check_signal_cooldown,
    record_signal_time,
    get_user_winrate_stats,
    get_user_pnl_stats,
    user_exists,
    VIP_PLANS,
    set_user_vip_plan,
    get_user_vip_status,
    set_user_phone,
    get_user_phone,
    create_vip_payment_request,
    get_vip_payment_request,
    update_vip_payment_status,
    get_pending_vip_requests,
    set_vip_card_info,
    get_vip_card_info,
    get_user_display_info,
)

from settings import init_settings, get_settings
from admin_tools import (
    dashboard,
    toggle_signal,
    toggle_bot_lock,
    toggle_channel_lock,
    set_daily_signal_limit,
    set_referral_step,
    report
)

# ============ تنظیمات اولیه ============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 816822644))
SUPPORT_ID = "@RealSurprise"
CHANNEL_ID_ENV = os.getenv("CHANNEL_ID")  # مقدار اولیه از متغیر محیطی (فallback)

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN not set!")


def get_channel_id():
    """
    آیدی کانال رو برمی‌گردونه: اول از دیتابیس (که از پنل ادمین قابل تنظیمه)،
    اگه چیزی ذخیره نشده بود، از متغیر محیطی CHANNEL_ID.
    """
    from database import get_setting
    db_value = get_setting('channel_id')
    return db_value if db_value else CHANNEL_ID_ENV

TEHRAN_TZ = pytz.timezone('Asia/Tehran')


# ============ کیبورد انتخاب زبان ============
def language_keyboard():
    keyboard = [
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ============ کیبورد انتخاب استراتژی (کاربر عادی) ============
def user_strategy_keyboard(lang='fa'):
    """
    لیست همه‌ی استراتژی‌های کشف‌شده رو برای انتخاب کاربر نشون می‌ده.
    خودکار از strategy_registry می‌خونه - افزودن استراتژی جدید (یک فایل
    در strategies/) بدون تغییر این تابع، خودش این‌جا ظاهر می‌شه.
    """
    from strategy_registry import get_all_strategies
    strategies = get_all_strategies()

    keyboard = []
    for strategy_id, module in strategies.items():
        name = module.STRATEGY_INFO.get("display_name", strategy_id)
        keyboard.append([InlineKeyboardButton(name, callback_data=f"user_strat_{strategy_id}")])

    keyboard.append([InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


# ============ کیبورد انتخاب نماد معاملاتی ============
SYMBOL_OPTIONS = {
    "gold": ("🥇 طلا (XAU/USD)", "XAU/USD"),
    "btc": ("₿ بیت‌کوین (BTC/USD)", "BTC/USD"),
}


def symbol_keyboard(lang='fa'):
    keyboard = []
    for key, (label, _) in SYMBOL_OPTIONS.items():
        keyboard.append([InlineKeyboardButton(label, callback_data=f"symbol_{key}")])
    keyboard.append([InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def live_price_symbol_keyboard(lang='fa'):
    """انتخاب نماد مخصوص دکمه‌ی «قیمت لحظه‌ای» - مستقل از مسیر دریافت سیگنال."""
    keyboard = []
    for key, (label, _) in SYMBOL_OPTIONS.items():
        keyboard.append([InlineKeyboardButton(label, callback_data=f"liveprice_symbol_{key}")])
    keyboard.append([InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="back")])
    return InlineKeyboardMarkup(keyboard)



# ============ کیبورد انتخاب RR (۱ تا ۱۰) ============
def rr_keyboard(lang='fa'):
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="rr_1"),
            InlineKeyboardButton("2", callback_data="rr_2"),
            InlineKeyboardButton("3", callback_data="rr_3"),
            InlineKeyboardButton("4", callback_data="rr_4"),
            InlineKeyboardButton("5", callback_data="rr_5")
        ],
        [
            InlineKeyboardButton("6", callback_data="rr_6"),
            InlineKeyboardButton("7", callback_data="rr_7"),
            InlineKeyboardButton("8", callback_data="rr_8"),
            InlineKeyboardButton("9", callback_data="rr_9"),
            InlineKeyboardButton("10", callback_data="rr_10")
        ],
        [InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ============ کیبورد اصلی کاربر ============
# ===== لیست دکمه‌های اصلی کاربر که از پنل ادمین قابل مدیریتن =====
# هر ورودی: (button_key, callback_data, لیبل زبان پیش‌فرض)
MANAGEABLE_USER_BUTTONS = [
    ("signal_btn", "signal_menu", "signal_btn"),
    ("performance_btn", "performance", "performance_btn"),
    ("history_btn", "history", "history_btn"),
    ("price_btn", "live_price", "price_btn"),
    ("vip_btn", "vip", "vip_btn"),
    ("referral_btn", "referral", "referral_btn"),
    ("settings_btn", "settings", "settings_btn"),
    ("support_btn", "support", "support_btn"),
]


def user_keyboard(lang='fa'):
    from database import get_button_label, is_button_hidden, get_all_custom_buttons

    rows = []
    # دو دکمه در هر ردیف، مگر دکمه‌ی سیگنال که تنهاست
    visible_buttons = []
    for button_key, callback, lang_key in MANAGEABLE_USER_BUTTONS:
        if is_button_hidden(button_key):
            continue
        default_label = get_text(lang, lang_key)
        label = get_button_label(button_key, default_label)
        visible_buttons.append((label, callback))

    # دکمه‌ی سیگنال (اولی) همیشه تنها تو یه ردیف، بقیه دوتا-دوتا
    if visible_buttons:
        rows.append([InlineKeyboardButton(visible_buttons[0][0], callback_data=visible_buttons[0][1])])
        remaining = visible_buttons[1:]
        for i in range(0, len(remaining), 2):
            pair = remaining[i:i + 2]
            rows.append([InlineKeyboardButton(lbl, callback_data=cb) for lbl, cb in pair])

    # ===== دکمه‌های کاملاً سفارشی که ادمین ساخته =====
    custom_buttons = get_all_custom_buttons()
    for i in range(0, len(custom_buttons), 2):
        pair = custom_buttons[i:i + 2]
        rows.append([
            InlineKeyboardButton(btn['label'], callback_data=f"custom_btn_{btn['button_key']}")
            for btn in pair
        ])

    rows.append([InlineKeyboardButton("🌍 " + get_text(lang, 'change_lang'), callback_data="change_lang")])

    return InlineKeyboardMarkup(rows)


# ============ کیبورد نتیجه سیگنال ============
# ============ کیبورد ادمین ============
def admin_keyboard():
    pending_count = len(get_pending_vip_requests())
    vip_requests_label = f"🧾 درخواست‌های VIP ({pending_count})" if pending_count else "🧾 درخواست‌های VIP"

    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")],
        [
            InlineKeyboardButton("👥 Users", callback_data="users"),
            InlineKeyboardButton("📈 Analytics", callback_data="analytics")
        ],
        [
            InlineKeyboardButton("📊 Set Daily Signal", callback_data="set_daily_signal"),
            InlineKeyboardButton("🔄 قانون رفرال", callback_data="set_referral_step")
        ],
        [
            InlineKeyboardButton("🔄 Reset Signals", callback_data="reset_signals"),
            InlineKeyboardButton("🔒 Bot Lock", callback_data="bot_lock"),
        ],
        [
            InlineKeyboardButton("🚀 Signal Control", callback_data="signal_control"),
            InlineKeyboardButton("🔒 Channel Lock", callback_data="channel_lock"),
        ],
        [
            InlineKeyboardButton("📢 تنظیم آیدی کانال", callback_data="set_channel_id")
        ],
        [
            InlineKeyboardButton("👑 مدیریت VIP", callback_data="vip_admin_menu"),
            InlineKeyboardButton(vip_requests_label, callback_data="vip_requests_list"),
        ],
        [
            InlineKeyboardButton("💳 شماره کارت VIP", callback_data="set_vip_card"),
        ],
        [
            InlineKeyboardButton("🗑️ Delete User", callback_data="delete_user"),
            InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")
        ],
        [InlineKeyboardButton("📊 Reports", callback_data="reports")],
        [
            InlineKeyboardButton("📏 فاصله‌ی استاپ (پیپ)", callback_data="set_stop_distance"),
            InlineKeyboardButton("⏱️ تایم‌فریم پیش‌فرض", callback_data="set_default_timeframe"),
        ],
        [
            InlineKeyboardButton("⏳ فاصله‌ی بین سیگنال‌ها", callback_data="set_signal_cooldown"),
        ],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ============ کیبورد رفرال ============
def referral_keyboard(user_id, lang='fa'):
    link = get_referral_link(user_id)
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'copy_link'), url=link)],
        [InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ============ کیبورد پلن‌های VIP ============
def vip_plans_keyboard(lang='fa'):
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'vip_plan_btn_1m'), callback_data="vip_plan_1m")],
        [InlineKeyboardButton(get_text(lang, 'vip_plan_btn_3m'), callback_data="vip_plan_3m")],
        [InlineKeyboardButton(get_text(lang, 'vip_plan_btn_6m'), callback_data="vip_plan_6m")],
        [InlineKeyboardButton(get_text(lang, 'vip_plan_btn_12m'), callback_data="vip_plan_12m")],
        [InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)


def vip_paid_keyboard(lang='fa'):
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'vip_paid_btn'), callback_data="vip_paid_confirm")],
        [InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="vip")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ============ چک کردن عضویت در کانال ============
async def check_channel_membership(user_id, context):
    from database import get_setting

    # ===== قفل کانال باید هم فعال باشه (از دکمه‌ی Channel Lock) و هم آیدی کانال تنظیم شده باشه =====
    if get_setting('channel_locked') != 'true':
        return True

    channel_id = get_channel_id()
    if not channel_id:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.warning(f"خطا در بررسی عضویت کانال برای کاربر {user_id}: {e}")
        return False


# ============ ارسال سیگنال ============
async def send_signal(bot, chat_id, trade_id, signal, analysis, df, timeframe, user_id, lang='fa', symbol='XAU/USD', current_price=None, mode='standard'):
    if current_price is None:
        # ===== اجرا در thread جدا تا event loop اصلی ربات فریز نشه =====
        # ===== (get_current_price از requests استفاده می‌کنه که blocking است) =====
        current_price = await _run_in_signal_thread(get_current_price, symbol)
    tehran_time = get_tehran_time()

    if not current_price:
        current_price = df['Close'].iloc[-1]

    # ===== entry/sl/tp از قبل (قبل از save_trade) با قیمت لحظه‌ای به‌روز شدن =====
    # اینجا دیگه نیازی به محاسبه‌ی دوباره نیست - از مقادیر نهایی که در
    # دیتابیس هم ذخیره شدن استفاده می‌کنیم تا پیام و رکورد دیتابیس همیشه
    # دقیقاً یکی باشن.
    entry = signal['entry']
    sl = signal['sl']
    tp = signal['tp']

    # ===== مود (Fast Scalp/Standard) حذف شده - RR همیشه از ستون استاندارد خونده می‌شه =====
    rr_ratio = get_user_rr(user_id, mode=mode)

    reasons_text = "\n".join([f"• {r}" for r in analysis.get('reasons', ['No reason recorded'])])
    style = analysis.get('style', 'Surpri3e Strategy')
    strength = signal.get('strength', 'NORMAL')

    title_prefix = "⚠️ " if strength == "WEAK" else "🚨 "

    # ============================================================
    # ⚠️ تصمیم پروژه: متن سیگنال صفر تا صد همیشه انگلیسیه، حتی وقتی
    # زبان ربات فارسیه. بر خلاف بقیه‌ی متن‌های ربات، این پیام از سیستم
    # چندزبانه (get_text) استفاده نمی‌کنه و مستقیم هاردکد انگلیسیه.
    # ============================================================
    message = f"""
{title_prefix}**SIGNAL ALERT**

**💱 Symbol:** {symbol}
**📊 Strategy:** {style}
**📈 Direction:** {'🟢 BUY' if signal['direction'] == 'BUY' else '🔴 SELL'}
**📍 Entry:** {entry:.2f}
**🛑 Stop Loss:** {sl:.2f}
**🎯 Take Profit:** {tp:.2f}
**🎯 Risk/Reward:** 1:{rr_ratio:.1f}

**📝 Reasons:**
{reasons_text}

⏱️ **Timeframe:** {timeframe}
💰 **Current Price:** {current_price:.2f}
🕐 **Time:** {tehran_time.strftime('%Y-%m-%d %H:%M:%S')}

ℹ️ The result of this trade (TP/SL) will be automatically tracked and reported.
"""

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown'
        )
    except Exception as e:
        # ===== محافظت نهایی: اگر به هر دلیلی (مثلاً یک کاراکتر خاص که از
        # این تابع فرار کرده) پارس Markdown شکست خورد، پیام را بدون
        # فرمت‌دهی (متن ساده) دوباره می‌فرستیم تا کاربر حداقل سیگنال را
        # از دست ندهد. =====
        logger.warning(f"ارسال پیام سیگنال با Markdown ناموفق بود، تلاش دوباره بدون فرمت‌دهی: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=message.replace('*', '').replace('_', '').replace('`', '')
        )


# ============ دستور /start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if context.args and context.args[0].startswith('ref_'):
        try:
            referrer_id = int(context.args[0].replace('ref_', ''))
            process_referral(user_id, referrer_id)
        except ValueError:
            pass

    if get_setting('bot_locked') == 'true':
        await update.message.reply_text("🔒 ربات در حال حاضر قفل است.")
        return

    is_member = await check_channel_membership(user_id, context)
    if not is_member:
        channel_id = get_channel_id()
        await update.message.reply_text(
            f"🔒 برای استفاده از ربات باید عضو کانال ما شوید:\n\n📢 {channel_id}\n\nپس از عضویت، دوباره /start را بزنید."
        )
        return

    # ===== فقط کاربر جدید صفحه‌ی انتخاب زبان رو می‌بینه =====
    # کاربر قدیمی مستقیم می‌ره سراغ منوی اصلی؛ برای تغییر زبان باید از
    # دکمه‌ی «تغییر زبان» داخل منوی تنظیمات استفاده کنه.
    if user_exists(user_id):
        lang = get_user_lang(user_id)
        context.user_data['lang'] = lang
        await update.message.reply_text(
            get_text(lang, 'welcome_back'),
            reply_markup=user_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    await update.message.reply_text(
        "🌍 **زبان خود را انتخاب کنید / Choose your language:**",
        reply_markup=language_keyboard(),
        parse_mode='Markdown'
    )


# ============ دستور /admin ============
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ دسترسی ندارید!")
        return

    await update.message.reply_text(
        "🤖 **پنل ادمین**\n\nمدیریت کامل ربات:",
        reply_markup=admin_keyboard(),
        parse_mode='Markdown'
    )


# ============ کمکی: پاسخ امن به ادمین چه پیام عکس‌دار باشه چه متنی ============
async def _reply_admin_panel(query, text):
    """
    ⚠️ رفع باگ: وقتی درخواست VIP با عکس رسید نمایش داده می‌شه (send_photo)،
    پیام یک "پیام عکس‌دار با کپشن" است - نه پیام متنی خالص. تلاش برای
    query.edit_message_text روی چنین پیامی خطای تلگرام
    "There is no text in the message to edit" می‌ده و کل هندلر می‌ترکه
    (که باعث می‌شد دکمه‌ی تایید/رد هیچ واکنشی نشون نده).

    این تابع تشخیص می‌ده پیام عکس‌دار است یا نه و از متد درست
    (edit_message_caption یا edit_message_text) استفاده می‌کنه. اگه به
    هر دلیلی هردو شکست بخوره (مثلاً پیام خیلی قدیمی شده)، به‌جای کرش
    کردن، یک پیام تازه می‌فرسته تا ادمین همیشه یک فیدبک ببینه.
    """
    try:
        if query.message and query.message.photo:
            await query.edit_message_caption(caption=text, reply_markup=admin_keyboard(), parse_mode='Markdown')
        else:
            await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode='Markdown')
    except Exception as e:
        logger.warning(f"ویرایش پیام ادمین ناموفق بود، پیام تازه ارسال می‌شود: {e}")
        try:
            await query.message.reply_text(text, reply_markup=admin_keyboard(), parse_mode='Markdown')
        except Exception as e2:
            logger.error(f"ارسال پیام تازه به ادمین هم ناموفق بود: {e2}")


# ============ مدیریت دکمه‌ها ============
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # ===== دکمه‌های کاملاً سفارشی (باید همین اول پردازش بشه تا اگه به یک
    # عملکرد موجود وصل شده، بتونه data رو عوض کنه و بقیه‌ی چک‌های پایین‌تر
    # این تابع رو با data جدید طی کنه - مهم نیست اون عملکرد کجای تابع باشه) =====
    if data.startswith("custom_btn_"):
        button_key = data.replace("custom_btn_", "")
        lang = context.user_data.get('lang') or get_user_lang(user_id)

        from database import get_custom_button
        btn = get_custom_button(button_key)

        if btn and btn.get('link_action'):
            data = btn['link_action']
            # عمداً return نمی‌کنیم؛ پردازش با data جدید در همین تابع ادامه پیدا می‌کنه
        elif btn:
            await query.edit_message_text(
                btn['response_text'],
                reply_markup=user_keyboard(lang),
                parse_mode='Markdown'
            )
            return
        else:
            await query.edit_message_text(
                get_text(lang, 'welcome_back'),
                reply_markup=user_keyboard(lang),
                parse_mode='Markdown'
            )
            return

    # ===== انتخاب زبان =====
    if data.startswith("lang_"):
        lang = data.replace("lang_", "")
        context.user_data['lang'] = lang
        add_user(user_id, lang=lang)

        await query.edit_message_text(
            get_text(lang, 'select_strategy'),
            reply_markup=user_strategy_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    # ===== انتخاب استراتژی (کاربر عادی) - بعدش مستقیم می‌ره سراغ انتخاب RR =====
    # ===== مود (Fast Scalp/Standard) و انتخاب تایم‌فریم حذف شدن - تایم‌فریم =====
    # ===== الان سراسری از پنل ادمین تنظیم می‌شه (get_setting('default_timeframe')) =====
    if data.startswith("user_strat_"):
        strategy_id = data.replace("user_strat_", "")
        lang = context.user_data.get('lang') or get_user_lang(user_id)

        context.user_data['style'] = strategy_id
        # ===== تایم‌فریم دیگه توسط کاربر انتخاب نمی‌شه - همیشه از تنظیمات سراسری ادمین میاد =====
        context.user_data['timeframe'] = get_setting('default_timeframe') or '5min'

        conn = connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET style=? WHERE id=?", (strategy_id, user_id))
        conn.commit()
        conn.close()

        await query.edit_message_text(
            get_text(lang, 'select_rr'),
            reply_markup=rr_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    # ===== تغییر زبان =====
    if data == "change_lang":
        await query.edit_message_text(
            "🌍 **زبان خود را انتخاب کنید / Choose your language:**",
            reply_markup=language_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== انتخاب RR (اختصاصی همین کاربر) - بازه محدود به ۱ تا ۵ =====
    if data.startswith("rr_"):
        rr = int(data.replace("rr_", ""))
        rr = max(1, min(5, rr))

        # ===== مود حذف شده - همیشه از همون ستون rr_ratio_standard استفاده می‌کنیم =====
        set_user_rr(user_id, rr, mode='standard')
        context.user_data['rr'] = rr

        lang = context.user_data.get('lang') or get_user_lang(user_id)
        style = context.user_data.get('style') or get_user_style(user_id)
        timeframe = context.user_data.get('timeframe', '5min')
        symbol = context.user_data.get('symbol', 'XAU/USD')

        signals_left = get_user_signals_left(user_id)
        if signals_left <= 0:
            await query.edit_message_text(
                get_text(lang, 'no_signals_left'),
                reply_markup=user_keyboard(lang),
                parse_mode='Markdown'
            )
            return

        # ===== چک بسته بودن بازار (فقط برای طلا/فارکس - کریپتو همیشه بازه) =====
        if not is_market_open(symbol):
            await query.edit_message_text(
                get_text(lang, 'market_closed'),
                reply_markup=user_keyboard(lang),
                parse_mode='Markdown'
            )
            return

        # ===== محدودیت زمانی ثابت بین دو سیگنال (سراسری، به‌جز ادمین) =====
        allowed, seconds_left = check_signal_cooldown(user_id, timeframe)
        if not allowed:
            minutes = seconds_left // 60
            seconds = seconds_left % 60
            wait_text = f"{minutes} دقیقه و {seconds} ثانیه" if minutes > 0 else f"{seconds} ثانیه"

            cooldown_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text(lang, 'cooldown_refresh_btn'), callback_data="signal_menu")],
                [InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="back")]
            ])

            await query.edit_message_text(
                get_text(lang, 'signal_cooldown').format(wait=wait_text),
                reply_markup=cooldown_keyboard,
                parse_mode='Markdown'
            )
            return

        await query.edit_message_text(
            get_text(lang, 'analyzing').format(timeframe=timeframe),
            parse_mode='Markdown'
        )

        try:
            # ===== حلقه‌ی تلاش مجدد واقعی =====
            # به‌جای یک بار گرفتن دیتا و تسلیم شدن، ربات چند بار (با فاصله)
            # دوباره از API دیتای تازه می‌گیره و دوباره تحلیل می‌کنه، تا وقتی
            # یا سیگنال معتبر پیدا بشه یا به سقف زمانی برسه. هر تلاش، تحلیل
            # واقعیه - نه صرفاً تاخیر مصنوعی.
            loading_frames = [
                get_text(lang, 'loading_frame_1'),
                get_text(lang, 'loading_frame_2'),
                get_text(lang, 'loading_frame_3'),
                get_text(lang, 'loading_frame_4'),
            ]

            MAX_WAIT_SECONDS = 90   # سقف زمانی که کاربر منتظر می‌مونه
            RETRY_INTERVAL = 4      # فاصله‌ی بین هر تلاش تحلیل

            signal, analysis, df = None, None, None
            elapsed = 0
            frame_index = 0

            # ===== مود (Fast Scalp/Standard) حذف شده - RR همیشه استاندارد است =====
            user_rr = get_user_rr(user_id, mode='standard')

            while elapsed < MAX_WAIT_SECONDS:
                # ===== اجرا در thread جدا تا event loop اصلی ربات فریز نشه =====
                # ===== (get_gold_candles از requests استفاده می‌کنه که blocking است؛ =====
                # ===== قبلاً این حلقه کل ربات رو برای همه‌ی کاربرا کند می‌کرد) =====
                df = await _run_in_signal_thread(get_gold_candles, timeframe, symbol=symbol)

                if df is not None and not df.empty:
                    signal, analysis = create_signal(df, style, rr_override=user_rr, symbol=symbol, timeframe=timeframe)
                    if signal:
                        break  # سیگنال معتبر پیدا شد - از حلقه خارج شو

                try:
                    await query.edit_message_text(
                        loading_frames[frame_index % len(loading_frames)],
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass  # rate limit یا پیام بدون تغییر - نادیده بگیر و ادامه بده

                await asyncio.sleep(RETRY_INTERVAL)
                elapsed += RETRY_INTERVAL
                frame_index += 1

            if df is not None and not df.empty:
                if signal:
                    strength = signal.get('strength', 'NORMAL')

                    # ===== به‌روزرسانی entry/sl/tp با قیمت لحظه‌ای واقعی قبل از ذخیره =====
                    # این کار باید قبل از save_trade انجام بشه، وگرنه دیتابیس (و چک
                    # خودکار TP/SL) با اعداد قدیمی کار می‌کنه که با چیزی که به
                    # کاربر نشون داده می‌شه فرق داره.
                    live_price = await _run_in_signal_thread(get_current_price, symbol)
                    if not live_price:
                        live_price = df['Close'].iloc[-1]

                    risk_distance = abs(signal['entry'] - signal['sl'])
                    reward_distance = abs(signal['tp'] - signal['entry'])
                    new_entry = round(float(live_price), 2)

                    if signal['direction'] == 'BUY':
                        signal['sl'] = round(new_entry - risk_distance, 2)
                        signal['tp'] = round(new_entry + reward_distance, 2)
                    else:
                        signal['sl'] = round(new_entry + risk_distance, 2)
                        signal['tp'] = round(new_entry - reward_distance, 2)
                    signal['entry'] = new_entry

                    trade_id = save_trade(signal, user_id, style, strength, symbol=symbol)
                    use_signal(user_id)
                    record_signal_time(user_id, timeframe)  # ثبت زمان برای cooldown بعدی

                    # ===== پاک کردن پیام لودینگ قبل از نمایش نتیجه =====
                    try:
                        await query.message.delete()
                    except Exception:
                        pass

                    await send_signal(context.bot, user_id, trade_id, signal, analysis, df, timeframe, user_id, lang, symbol=symbol, current_price=live_price)
                else:
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=get_text(lang, 'no_signal'),
                        reply_markup=user_keyboard(lang),
                        parse_mode='Markdown'
                    )
            else:
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await context.bot.send_message(
                    chat_id=user_id,
                    text=get_text(lang, 'error'),
                    reply_markup=user_keyboard(lang),
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.exception(f"خطا در تولید سیگنال برای کاربر {user_id}")
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ {get_text(lang, 'error')}: {str(e)}",
                reply_markup=user_keyboard(lang),
                parse_mode='Markdown'
            )
        return

    # ===== چک کردن قفل ربات =====
    if get_setting('bot_locked') == 'true' and user_id != ADMIN_ID:
        await query.edit_message_text("🔒 ربات قفل است.")
        return

    # ===== چک کردن عضویت در کانال =====
    if user_id != ADMIN_ID:
        is_member = await check_channel_membership(user_id, context)
        if not is_member:
            channel_id = get_channel_id()
            await query.edit_message_text(f"🔒 برای استفاده از ربات باید عضو کانال ما شوید:\n\n📢 {channel_id}")
            return

    # ===== برگشت =====
    if data == "back":
        context.user_data['admin_action'] = None
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            get_text(lang, 'welcome_back'),
            reply_markup=user_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    # ===== رفرال =====
    if data == "referral":
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        link = get_referral_link(user_id)
        await query.edit_message_text(
            get_text(lang, 'referral_text').format(link=link),
            reply_markup=referral_keyboard(user_id, lang),
            parse_mode='Markdown'
        )
        return

    # ===== قیمت لحظه‌ای =====
    if data == "live_price":
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            "💱 **نماد مورد نظر برای دیدن قیمت لحظه‌ای را انتخاب کنید:**",
            reply_markup=live_price_symbol_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    if data.startswith("liveprice_symbol_"):
        symbol_key = data.replace("liveprice_symbol_", "")
        symbol = SYMBOL_OPTIONS.get(symbol_key, ("", "XAU/USD"))[1]
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(get_text(lang, 'fetching_price'), parse_mode='Markdown')

        try:
            price = await _run_in_signal_thread(get_current_price, symbol)
            tehran_time = get_tehran_time()

            if price:
                await query.edit_message_text(
                    f"💱 **{symbol}**\n\n" + get_text(lang, 'price_result').format(price=price, time=tehran_time.strftime('%H:%M:%S')),
                    reply_markup=user_keyboard(lang),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    get_text(lang, 'price_error'),
                    reply_markup=user_keyboard(lang),
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.exception(f"خطا در دریافت قیمت لحظه‌ای برای کاربر {user_id}")
            await query.edit_message_text(
                f"❌ **{get_text(lang, 'error')}:** {str(e)}",
                reply_markup=user_keyboard(lang),
                parse_mode='Markdown'
            )
        return

    # ===== پشتیبانی =====
    if data == "support":
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            get_text(lang, 'support_text').format(support=SUPPORT_ID),
            reply_markup=user_keyboard(lang),
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        return

    # ===== منوی اصلی سیگنال =====
    if data == "signal_menu":
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            "💱 **نماد مورد نظر را انتخاب کنید:**",
            reply_markup=symbol_keyboard(lang),
            parse_mode='Markdown'
        )
        return


    if data.startswith("symbol_"):
        symbol_key = data.replace("symbol_", "")
        symbol_value = SYMBOL_OPTIONS.get(symbol_key, ("", "XAU/USD"))[1]
        context.user_data['symbol'] = symbol_value

        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            get_text(lang, 'select_strategy'),
            reply_markup=user_strategy_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    # ===== عملکرد =====
    if data == "performance":
        signals_left = get_user_signals_left(user_id)
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        keyboard = [
            [
                InlineKeyboardButton(get_text(lang, 'weekly_btn'), callback_data="perf_weekly"),
                InlineKeyboardButton(get_text(lang, 'monthly_btn'), callback_data="perf_monthly")
            ],
            [InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="back")]
        ]
        await query.edit_message_text(
            get_text(lang, 'performance_menu_text').format(left=signals_left),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    # ===== عملکرد هفتگی =====
    if data == "perf_weekly":
        stats = get_user_winrate_stats(user_id)
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        w = stats['weekly']
        keyboard = [
            [InlineKeyboardButton(get_text(lang, 'pnl_calc_btn'), callback_data="pnl_calc_weekly")],
            [InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="performance")]
        ]
        await query.edit_message_text(
            get_text(lang, 'weekly_performance_text').format(
                total=w['total'], wins=w['wins'], losses=w['losses'], winrate=w['winrate']
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    # ===== عملکرد ماهانه =====
    if data == "perf_monthly":
        stats = get_user_winrate_stats(user_id)
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        m = stats['monthly']
        keyboard = [
            [InlineKeyboardButton(get_text(lang, 'pnl_calc_btn'), callback_data="pnl_calc_monthly")],
            [InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="performance")]
        ]
        await query.edit_message_text(
            get_text(lang, 'monthly_performance_text').format(
                total=m['total'], wins=m['wins'], losses=m['losses'], winrate=m['winrate']
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    # ===== محاسبه‌ی سود/زیان بر اساس درصد ریسک ثابت کاربر =====
    if data == "pnl_calc_weekly" or data == "pnl_calc_monthly":
        period = 'weekly' if data == "pnl_calc_weekly" else 'monthly'
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        context.user_data['admin_action'] = 'pnl_awaiting_risk'
        context.user_data['pnl_period'] = period
        await query.edit_message_text(
            get_text(lang, 'pnl_ask_risk'),
            parse_mode='Markdown'
        )
        return

    # ===== تاریخچه =====
    if data == "history":
        trades = get_user_trades(user_id)
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        if trades:
            text = get_text(lang, 'history_title') + "\n\n"
            for i, t in enumerate(trades[:10], 1):
                emoji = "✅" if t['result'] == "TP" else "❌" if t['result'] == "SL" else "⏳"
                text += f"{i}. {t['direction']} | {t['entry']} | {emoji} {t['result']} | {t['style']}\n"
            await query.edit_message_text(text, reply_markup=user_keyboard(lang), parse_mode='Markdown')
        else:
            await query.edit_message_text(get_text(lang, 'no_history'), reply_markup=user_keyboard(lang), parse_mode='Markdown')
        return

    # ===== VIP =====
    if data == "vip":
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            get_text(lang, 'vip_intro_text'),
            reply_markup=vip_plans_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    if data.startswith("vip_plan_"):
        plan_id = data.replace("vip_plan_", "")
        lang = context.user_data.get('lang') or get_user_lang(user_id)

        if plan_id not in VIP_PLANS:
            return

        card_info = get_vip_card_info()
        if not card_info['card_number']:
            await query.edit_message_text(
                get_text(lang, 'vip_card_not_set'),
                reply_markup=vip_plans_keyboard(lang),
                parse_mode='Markdown'
            )
            return

        context.user_data['vip_selected_plan'] = plan_id
        plan = VIP_PLANS[plan_id]
        card_holder_line = f"👤 {card_info['card_holder']}" if card_info['card_holder'] else ""

        await query.edit_message_text(
            get_text(lang, 'vip_payment_card_text').format(
                plan=plan['label'],
                price=plan['price_toman'],
                card_number=card_info['card_number'],
                card_holder_line=card_holder_line
            ),
            reply_markup=vip_paid_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    if data == "vip_paid_confirm":
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        if not context.user_data.get('vip_selected_plan'):
            # ===== اگه کاربر بدون انتخاب پلن به این مرحله رسیده (مثلاً بعد از ری‌استارت ربات) =====
            await query.edit_message_text(
                get_text(lang, 'vip_intro_text'),
                reply_markup=vip_plans_keyboard(lang),
                parse_mode='Markdown'
            )
            return

        context.user_data['admin_action'] = 'vip_awaiting_phone'
        await query.edit_message_text(
            get_text(lang, 'vip_ask_phone'),
            parse_mode='Markdown'
        )
        return

    # ===== تنظیمات =====
    if data == "settings":
        settings = get_settings()
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        style = context.user_data.get('style') or get_user_style(user_id)
        signals_left = get_user_signals_left(user_id)

        vip_status = get_user_vip_status(user_id)
        if vip_status['is_vip']:
            vip_line = get_text(lang, 'vip_status_active').format(
                plan=vip_status['plan_label'] or '—',
                days_left=vip_status['days_left'] if vip_status['days_left'] is not None else '∞'
            )
        else:
            vip_line = get_text(lang, 'vip_status_none')

        await query.edit_message_text(
            get_text(lang, 'settings_text').format(
                status='🟢 ' + get_text(lang, 'online') if settings.get('status', True) else '🔴 ' + get_text(lang, 'offline'),
                style=style,
                lang=lang,
                signals_left=signals_left,
                vip_line=vip_line
            ),
            reply_markup=user_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    # ============================================
    # ===== پنل ادمین =====
    # ============================================

    if data == "dashboard":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(dashboard(), reply_markup=admin_keyboard(), parse_mode='Markdown')
        return

    if data == "admin_back":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(dashboard(), reply_markup=admin_keyboard(), parse_mode='Markdown')
        return

    if data == "users":
        if user_id != ADMIN_ID:
            return
        users = get_all_users()
        text = f"👥 **کاربران**\n\n**کل:** {len(users)}\n\n"
        for u in users[:20]:
            text += f"🆔 {u['id']} | {'👑 VIP' if u['is_vip'] else '👤 عادی'} | {u['referral_count']} رفرال | {u['lang']} | {u['style']}\n"
        await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode='Markdown')
        return

    if data == "analytics":
        if user_id != ADMIN_ID:
            return
        stats = get_statistics()
        today_stats = get_today_stats()
        await query.edit_message_text(
            f"📈 **تحلیل پیشرفته**\n\n"
            f"📊 **کل معاملات:** {stats['total']}\n"
            f"✅ **برنده:** {stats['wins']}\n"
            f"❌ **بازنده:** {stats['losses']}\n"
            f"🎯 **نرخ موفقیت:** {stats['winrate']}%\n\n"
            f"📊 **آمار امروز:**\n"
            f"• سیگنال‌های استفاده شده: {today_stats['signals_used']}\n"
            f"• TP ثبت شده: {today_stats['tp_count']}\n"
            f"• SL ثبت شده: {today_stats['sl_count']}",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== تنظیمات ادمین =====
    if data == "set_daily_signal":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(
            "📊 **تعداد سیگنال روزانه**\n\nعدد را وارد کنید (مثلاً 5):",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'set_daily_signal'
        return

    if data == "set_stop_distance":
        if user_id != ADMIN_ID:
            return
        current = get_setting('stop_distance_pips') or '30'
        await query.edit_message_text(
            f"📏 **فاصله‌ی استاپ (پیپ)**\n\n"
            f"فعلی: {current} پیپ\n\n"
            f"این فاصله بین Entry و SL برای همه‌ی کاربران و همه‌ی نمادها یکسان اعمال می‌شود.\n"
            f"عدد پیپ جدید را وارد کنید (مثلاً 30):",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'set_stop_distance'
        return

    if data == "set_default_timeframe":
        if user_id != ADMIN_ID:
            return
        current = get_setting('default_timeframe') or '5min'
        await query.edit_message_text(
            f"⏱️ **تایم‌فریم پیش‌فرض**\n\n"
            f"فعلی: {current}\n\n"
            f"این تایم‌فریم برای همه‌ی کاربران به‌صورت یکسان اعمال می‌شود (کاربر دیگر خودش انتخاب نمی‌کند).\n"
            f"گزینه‌های مجاز: 1min, 5min, 15min, 30min, 1h, 4h, 1d\n"
            f"یکی را تایپ کنید:",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'set_default_timeframe'
        return

    if data == "set_signal_cooldown":
        if user_id != ADMIN_ID:
            return
        current = get_setting('signal_cooldown_minutes') or '15'
        await query.edit_message_text(
            f"⏳ **فاصله‌ی بین سیگنال‌ها**\n\n"
            f"فعلی: {current} دقیقه\n\n"
            f"این فاصله‌ی زمانی الزامی بین دو سیگنال متوالی هر کاربر است (به‌جز ادمین که معاف است).\n"
            f"عدد دقیقه‌ی جدید را وارد کنید (مثلاً 15):",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'set_signal_cooldown'
        return

    if data == "set_referral_step":
        if user_id != ADMIN_ID:
            return
        current_count = get_setting('referral_step_count') or '5'
        current_bonus = get_setting('referral_step_bonus') or '3'
        await query.edit_message_text(
            f"🔄 **قانون رفرال**\n\n"
            f"فعلی: هر {current_count} نفر رفرال ⇽ {current_bonus} سیگنال اضافه\n\n"
            f"دو عدد رو با کاما بفرست: `تعداد_رفرال,تعداد_سیگنال_اضافه`\n"
            f"مثال: `5,3` یعنی هر ۵ نفر رفرال، ۳ سیگنال اضافه به سقف روزانه اضافه بشه.",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'set_referral_step'
        return

    # ===== کنترل‌ها =====
    if data == "reset_signals":
        if user_id != ADMIN_ID:
            return
        reset_daily_signals()
        await query.edit_message_text("🔄 **سیگنال‌های روزانه ریست شد!**", reply_markup=admin_keyboard(), parse_mode='Markdown')
        return

    if data == "bot_lock":
        if user_id != ADMIN_ID:
            return
        status = toggle_bot_lock()
        await query.edit_message_text(f"🔒 **قفل ربات:** {status}", reply_markup=admin_keyboard(), parse_mode='Markdown')
        return

    if data == "signal_control":
        if user_id != ADMIN_ID:
            return
        status = toggle_signal()
        await query.edit_message_text(f"🚀 **کنترل سیگنال:** {status}", reply_markup=admin_keyboard(), parse_mode='Markdown')
        return

    if data == "channel_lock":
        if user_id != ADMIN_ID:
            return
        status = toggle_channel_lock()
        current_channel = get_channel_id()
        note = "" if current_channel else "\n\n⚠️ توجه: هنوز آیدی کانالی تنظیم نشده، پس این قفل عملاً اثری ندارد. از دکمه‌ی «تنظیم آیدی کانال» استفاده کنید."
        await query.edit_message_text(f"🔒 **قفل کانال:** {status}{note}", reply_markup=admin_keyboard(), parse_mode='Markdown')
        return

    if data == "set_channel_id":
        if user_id != ADMIN_ID:
            return
        current_channel = get_channel_id() or "(هنوز تنظیم نشده)"
        await query.edit_message_text(
            f"📢 **تنظیم آیدی کانال**\n\n"
            f"آیدی فعلی: `{current_channel}`\n\n"
            f"آیدی جدید کانال را بفرستید (مثال: `@mychannel` یا `-1001234567890`).\n\n"
            f"⚠️ ربات باید ادمین همان کانال باشد تا بتواند عضویت کاربران را بررسی کند.\n\n"
            f"برای حذف قفل کانال کامل، عبارت `حذف` را بفرستید.",
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'set_channel_id'
        return

    # ===== مدیریت VIP =====
    if data == "vip_admin_menu":
        if user_id != ADMIN_ID:
            return
        keyboard = [
            [InlineKeyboardButton("➕ VIP کردن دستی کاربر", callback_data="vip_user_manual")],
            [InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")]
        ]
        await query.edit_message_text(
            "👑 **مدیریت VIP**\n\n"
            "برای تایید پرداخت‌های ارسالی کاربران از «درخواست‌های VIP» در منوی اصلی ادمین استفاده کن.\n"
            "برای VIP کردن دستی (بدون فرآیند پرداخت) از گزینه‌ی زیر استفاده کن.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    if data == "vip_user_manual":
        if user_id != ADMIN_ID:
            return
        plan_lines = "\n".join(f"`{pid}` = {p['label']}" for pid, p in VIP_PLANS.items())
        await query.edit_message_text(
            f"👑 **VIP کردن دستی کاربر**\n\n"
            f"فرمت: `آیدی,پلن`\n\n"
            f"پلن‌های معتبر:\n{plan_lines}\n\n"
            f"مثال: `123456789,3m`",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'vip_user_manual'
        return

    if data == "set_vip_card":
        if user_id != ADMIN_ID:
            return
        card_info = get_vip_card_info()
        current = card_info['card_number'] or "(هنوز تنظیم نشده)"
        holder = card_info['card_holder'] or ""
        await query.edit_message_text(
            f"💳 **شماره کارت VIP**\n\n"
            f"فعلی: `{current}` {('- ' + holder) if holder else ''}\n\n"
            f"شماره کارت جدید رو بفرست. اگه می‌خوای نام صاحب کارت هم ثبت بشه،"
            f" با کاما بعدش بنویس.\nمثال: `6037-XXXX-XXXX-XXXX,علی رضایی`",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'set_vip_card'
        return

    if data == "vip_requests_list":
        if user_id != ADMIN_ID:
            return
        pending = get_pending_vip_requests()
        if not pending:
            await query.edit_message_text(
                "🧾 **درخواست‌های VIP**\n\nدرخواست در انتظاری وجود ندارد.",
                reply_markup=admin_keyboard(),
                parse_mode='Markdown'
            )
            return

        keyboard = []
        for req in pending[:20]:
            plan_label = VIP_PLANS.get(req['plan_id'], {}).get('label', req['plan_id'])
            keyboard.append([InlineKeyboardButton(
                f"#{req['id']} · {req['user_id']} · {plan_label}",
                callback_data=f"vip_req_view_{req['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")])

        await query.edit_message_text(
            f"🧾 **درخواست‌های VIP در انتظار ({len(pending)})**\n\nروی هرکدام بزن برای مشاهده‌ی جزئیات و رسید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    if data.startswith("vip_req_view_"):
        if user_id != ADMIN_ID:
            return
        request_id = int(data.replace("vip_req_view_", ""))
        req = get_vip_payment_request(request_id)
        if not req:
            await query.edit_message_text("❌ این درخواست پیدا نشد.", reply_markup=admin_keyboard())
            return

        plan_label = VIP_PLANS.get(req['plan_id'], {}).get('label', req['plan_id'])
        keyboard = [
            [
                InlineKeyboardButton("✅ تایید و VIP کن", callback_data=f"vip_req_approve_{request_id}"),
                InlineKeyboardButton("❌ رد کن", callback_data=f"vip_req_reject_{request_id}"),
            ],
            [InlineKeyboardButton("🔙 برگشت", callback_data="vip_requests_list")]
        ]

        caption = (
            f"🧾 **درخواست #{request_id}**\n\n"
            f"👤 کاربر: {get_user_display_info(req['user_id'])}\n"
            f"📦 پلن: {plan_label}\n"
            f"📞 شماره تماس: {req['phone_number'] or '—'}\n"
            f"وضعیت: {req['status']}"
        )

        try:
            if req['receipt_file_id']:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=req['receipt_file_id'],
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception as e:
            logger.warning(f"نمایش رسید VIP ناموفق بود: {e}")
            await query.edit_message_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    if data.startswith("vip_req_approve_"):
        if user_id != ADMIN_ID:
            return
        request_id = int(data.replace("vip_req_approve_", ""))
        req = get_vip_payment_request(request_id)
        if not req or req['status'] != 'PENDING':
            await _reply_admin_panel(query, "⚠️ این درخواست دیگر در انتظار نیست.")
            return

        set_user_vip_plan(req['user_id'], req['plan_id'])
        update_vip_payment_status(request_id, 'APPROVED')
        plan_label = VIP_PLANS.get(req['plan_id'], {}).get('label', req['plan_id'])

        await _reply_admin_panel(query, f"✅ کاربر {req['user_id']} با پلن {plan_label} VIP شد.")

        try:
            user_lang = get_user_lang(req['user_id'])
            await context.bot.send_message(
                chat_id=req['user_id'],
                text=get_text(user_lang, 'vip_approved').format(plan=plan_label),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"اطلاع‌رسانی تایید VIP به کاربر ناموفق بود: {e}")
        return

    if data.startswith("vip_req_reject_"):
        if user_id != ADMIN_ID:
            return
        request_id = int(data.replace("vip_req_reject_", ""))
        req = get_vip_payment_request(request_id)
        if not req or req['status'] != 'PENDING':
            await _reply_admin_panel(query, "⚠️ این درخواست دیگر در انتظار نیست.")
            return

        update_vip_payment_status(request_id, 'REJECTED')
        await _reply_admin_panel(query, f"❌ درخواست #{request_id} رد شد.")

        try:
            user_lang = get_user_lang(req['user_id'])
            await context.bot.send_message(
                chat_id=req['user_id'],
                text=get_text(user_lang, 'vip_rejected'),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"اطلاع‌رسانی رد VIP به کاربر ناموفق بود: {e}")
        return

    if data == "delete_user":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(
            "🗑️ **حذف کاربر**\n\nآیدی عددی کاربر را وارد کنید:",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'delete_user'
        return

    if data == "broadcast":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(
            "📢 **ارسال همگانی**\n\nپیام خود را تایپ کنید (یا /cancel برای لغو):",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['broadcast_mode'] = True
        return

    if data == "reports":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(report(), reply_markup=admin_keyboard(), parse_mode='Markdown')
        return


# ============ مدیریت پیام‌ها ============
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    عکس‌های ارسالی کاربر رو مدیریت می‌کنه. فعلاً تنها استفاده‌ی این هندلر،
    دریافت عکس رسید پرداخت VIP است (وقتی admin_action == 'vip_awaiting_receipt').
    سایر عکس‌ها (بدون این state) نادیده گرفته می‌شن.
    """
    user_id = update.effective_user.id
    update_activity(user_id)
    lang = context.user_data.get('lang') or get_user_lang(user_id)

    if context.user_data.get('admin_action') != 'vip_awaiting_receipt':
        return

    plan_id = context.user_data.get('vip_selected_plan')
    if not plan_id or plan_id not in VIP_PLANS:
        context.user_data['admin_action'] = None
        await update.message.reply_text(
            get_text(lang, 'vip_intro_text'),
            reply_markup=vip_plans_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    if not update.message.photo:
        await update.message.reply_text(get_text(lang, 'vip_receipt_not_photo'), parse_mode='Markdown')
        return

    # ===== بزرگترین سایز عکس رو می‌گیریم (بهترین کیفیت برای بررسی ادمین) =====
    file_id = update.message.photo[-1].file_id
    phone_number = get_user_phone(user_id)

    request_id = create_vip_payment_request(user_id, plan_id, phone_number, file_id)

    context.user_data['admin_action'] = None
    context.user_data['vip_selected_plan'] = None

    await update.message.reply_text(
        get_text(lang, 'vip_request_submitted'),
        reply_markup=user_keyboard(lang),
        parse_mode='Markdown'
    )

    # ===== فوروارد به ادمین با دکمه‌ی تایید/رد سریع =====
    plan_label = VIP_PLANS[plan_id]['label']
    caption = (
        f"🧾 **درخواست پرداخت VIP جدید (#{request_id})**\n\n"
        f"👤 کاربر: {get_user_display_info(user_id)}\n"
        f"📦 پلن: {plan_label}\n"
        f"📞 شماره تماس: {phone_number or '—'}"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ تایید و VIP کن", callback_data=f"vip_req_approve_{request_id}"),
            InlineKeyboardButton("❌ رد کن", callback_data=f"vip_req_reject_{request_id}"),
        ]
    ]
    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.warning(f"ارسال رسید VIP به ادمین ناموفق بود: {e}")


async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_activity(user_id)
    text = update.message.text

    if context.user_data.get('broadcast_mode', False):
        if user_id == ADMIN_ID:
            if text.lower() == '/cancel':
                context.user_data['broadcast_mode'] = False
                await update.message.reply_text("⏹️ **لغو شد.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
                return

            users = get_all_users()
            success = 0
            failed = 0
            for u in users:
                try:
                    await context.bot.send_message(chat_id=u['id'], text=f"{text}")
                    success += 1
                except Exception as e:
                    failed += 1
                    logger.warning(f"ارسال پیام همگانی به کاربر {u['id']} ناموفق بود: {e}")

            context.user_data['broadcast_mode'] = False
            await update.message.reply_text(
                f"✅ **ارسال شد!**\n\n✅ موفق: {success}\n❌ ناموفق: {failed}",
                reply_markup=admin_keyboard(),
                parse_mode='Markdown'
            )
        return

    if context.user_data.get('admin_action'):
        action = context.user_data['admin_action']

        if action == 'pnl_awaiting_risk':
            lang = context.user_data.get('lang') or get_user_lang(user_id)
            period = context.user_data.get('pnl_period', 'weekly')

            risk_text = text.strip().replace('%', '').replace(',', '.')
            try:
                risk_percent = float(risk_text)
                if risk_percent <= 0 or risk_percent > 100:
                    raise ValueError
            except ValueError:
                await update.message.reply_text(get_text(lang, 'pnl_invalid_risk'), parse_mode='Markdown')
                return

            stats = get_user_pnl_stats(user_id, risk_percent, period=period)
            period_label = get_text(lang, 'weekly_btn') if period == 'weekly' else get_text(lang, 'monthly_btn')

            if stats['total'] == 0:
                await update.message.reply_text(
                    get_text(lang, 'pnl_no_trades'),
                    reply_markup=user_keyboard(lang),
                    parse_mode='Markdown'
                )
                context.user_data['admin_action'] = None
                return

            pf_display = f"{stats['profit_factor']:.2f}" if stats['profit_factor'] is not None else "∞"

            await update.message.reply_text(
                get_text(lang, 'pnl_result_text').format(
                    period=period_label,
                    risk_percent=stats['risk_percent'],
                    total=stats['total'],
                    wins=stats['wins'],
                    losses=stats['losses'],
                    winrate=stats['winrate'],
                    profit_percent=stats['total_profit_percent'],
                    loss_percent=stats['total_loss_percent'],
                    net_percent=stats['net_percent'],
                    profit_factor=pf_display
                ),
                reply_markup=user_keyboard(lang),
                parse_mode='Markdown'
            )
            context.user_data['admin_action'] = None
            return

        if action == 'vip_awaiting_phone':
            lang = context.user_data.get('lang') or get_user_lang(user_id)
            phone_clean = text.strip().replace(' ', '').replace('-', '')

            # ===== اعتبارسنجی ساده‌ی شماره تماس ایرانی (۰۹ + ۹ رقم، یا با +98) =====
            import re as _re
            if not _re.match(r'^(0|\+?98)?9\d{9}$', phone_clean):
                await update.message.reply_text(
                    get_text(lang, 'vip_invalid_phone'),
                    parse_mode='Markdown'
                )
                return

            set_user_phone(user_id, phone_clean)
            context.user_data['admin_action'] = 'vip_awaiting_receipt'
            await update.message.reply_text(
                get_text(lang, 'vip_ask_receipt'),
                parse_mode='Markdown'
            )
            return

        if action == 'set_daily_signal':
            if text.isdigit():
                result = set_daily_signal_limit(int(text))
                await update.message.reply_text(result, reply_markup=admin_keyboard(), parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ **لطفاً یک عدد وارد کنید.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            context.user_data['admin_action'] = None
            return

        if action == 'set_referral_step':
            parts = [p.strip() for p in text.split(',')]
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                result = set_referral_step(parts[0], parts[1])
                await update.message.reply_text(result, reply_markup=admin_keyboard(), parse_mode='Markdown')
            else:
                await update.message.reply_text(
                    "❌ **فرمت درست:** `تعداد_رفرال,تعداد_سیگنال_اضافه` (مثال: `5,3`)",
                    reply_markup=admin_keyboard(), parse_mode='Markdown'
                )
            context.user_data['admin_action'] = None
            return

        if action == 'vip_user_manual':
            parts = [p.strip() for p in text.split(',')]
            if len(parts) == 2 and parts[0].isdigit() and parts[1] in VIP_PLANS:
                target_id, plan_id = int(parts[0]), parts[1]
                set_user_vip_plan(target_id, plan_id)
                plan_label = VIP_PLANS[plan_id]['label']
                await update.message.reply_text(
                    f"👑 **کاربر {target_id} با پلن {plan_label} VIP شد**",
                    reply_markup=admin_keyboard(), parse_mode='Markdown'
                )
                try:
                    user_lang = get_user_lang(target_id)
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=get_text(user_lang, 'vip_approved').format(plan=plan_label),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"اطلاع‌رسانی VIP دستی به کاربر ناموفق بود: {e}")
            else:
                plan_lines = "\n".join(f"`{pid}` = {p['label']}" for pid, p in VIP_PLANS.items())
                await update.message.reply_text(
                    f"❌ **فرمت درست:** `آیدی,پلن`\n\n{plan_lines}",
                    reply_markup=admin_keyboard(), parse_mode='Markdown'
                )
            context.user_data['admin_action'] = None
            return

        if action == 'set_vip_card':
            parts = [p.strip() for p in text.split(',', 1)]
            card_number = parts[0]
            card_holder = parts[1] if len(parts) > 1 else None
            set_vip_card_info(card_number, card_holder)
            await update.message.reply_text(
                "✅ **شماره کارت VIP بروزرسانی شد.**",
                reply_markup=admin_keyboard(), parse_mode='Markdown'
            )
            context.user_data['admin_action'] = None
            return

        if action == 'delete_user':
            if text.isdigit():
                delete_user(int(text))
                await update.message.reply_text(f"🗑️ **کاربر {text} حذف شد**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ **لطفاً آیدی عددی وارد کنید.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            context.user_data['admin_action'] = None
            return

        if action == 'set_stop_distance':
            context.user_data['admin_action'] = None
            from admin_tools import set_stop_distance_pips
            result = set_stop_distance_pips(text.replace(',', '.'))
            await update.message.reply_text(result, reply_markup=admin_keyboard(), parse_mode='Markdown')
            return

        if action == 'set_default_timeframe':
            context.user_data['admin_action'] = None
            from admin_tools import set_default_timeframe
            result = set_default_timeframe(text.strip())
            await update.message.reply_text(result, reply_markup=admin_keyboard(), parse_mode='Markdown')
            return

        if action == 'set_signal_cooldown':
            context.user_data['admin_action'] = None
            from admin_tools import set_signal_cooldown
            result = set_signal_cooldown(text.replace(',', '.'))
            await update.message.reply_text(result, reply_markup=admin_keyboard(), parse_mode='Markdown')
            return

        if action == 'set_channel_id':
            context.user_data['admin_action'] = None
            from database import update_setting

            if text.strip() in ('حذف', 'حذف کن', 'پاک کن', 'clear', 'remove'):
                update_setting('channel_id', '')
                await update.message.reply_text(
                    "✅ **آیدی کانال پاک شد.** از این پس چک عضویت کانال غیرفعال است.",
                    reply_markup=admin_keyboard(),
                    parse_mode='Markdown'
                )
                return

            new_channel_id = text.strip()
            update_setting('channel_id', new_channel_id)
            await update.message.reply_text(
                f"✅ **آیدی کانال به `{new_channel_id}` تنظیم شد.**\n\n"
                f"⚠️ یادتان باشد که ربات را ادمین همان کانال کنید تا بتواند عضویت کاربران را چک کند، "
                f"و از دکمه‌ی «Channel Lock» برای فعال کردن قفل استفاده کنید.",
                reply_markup=admin_keyboard(),
                parse_mode='Markdown'
            )
            return

    lang = context.user_data.get('lang') or get_user_lang(user_id)
    await update.message.reply_text(
        get_text(lang, 'use_buttons'),
        reply_markup=user_keyboard(lang),
        parse_mode='Markdown'
    )


# ============ اجرا ============
def main():
    try:
        init_settings()
        create_database()

        async def _post_init(application):
            """بعد از راه‌اندازی کامل ربات، حلقه‌ی چک خودکار TP/SL رو در پس‌زمینه اجرا می‌کنه."""
            from auto_tracker import auto_tracker_loop
            asyncio.create_task(auto_tracker_loop(application))

        app = Application.builder().token(TOKEN).post_init(_post_init).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("admin", admin))
        app.add_handler(CallbackQueryHandler(button))
        app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

        logging.info("🤖 Surpri3e AI Bot Started")
        print("✅ Surpri3e AI Bot Started")

        app.run_polling()

    except Exception as e:
        logging.error(f"❌ Main Error: {e}")
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
