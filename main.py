import os
import logging
import asyncio
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
)

from settings import init_settings, get_settings
from admin_tools import (
    dashboard,
    toggle_signal,
    toggle_bot_lock,
    toggle_channel_lock,
    set_daily_signal_limit,
    set_default_timeframe,
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
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ============ کیبورد انتخاب حالت معاملاتی (Surpri3e Strategy) ============
def mode_keyboard(lang='fa'):
    keyboard = [
        [InlineKeyboardButton("⚡ Fast Scalp (1min)", callback_data="mode_fast_scalp")],
        [InlineKeyboardButton("📈 Standard Mode", callback_data="mode_standard")],
        [InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="back")]
    ]
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


# ============ کیبورد تایم‌فریم برای Standard Mode (بدون 1min) ============
def timeframe_keyboard_standard(lang='fa'):
    keyboard = [
        [
            InlineKeyboardButton(get_text(lang, 'tf_5min'), callback_data="tf_5min"),
            InlineKeyboardButton(get_text(lang, 'tf_15min'), callback_data="tf_15min")
        ],
        [
            InlineKeyboardButton(get_text(lang, 'tf_1h'), callback_data="tf_1h"),
            InlineKeyboardButton(get_text(lang, 'tf_4h'), callback_data="tf_4h"),
            InlineKeyboardButton(get_text(lang, 'tf_1d'), callback_data="tf_1d")
        ],
        [InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="back")]
    ]
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
            InlineKeyboardButton("⏱️ Set Timeframe", callback_data="set_timeframe")
        ],
        [
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
        [InlineKeyboardButton("⚙️ مدیریت استراتژی‌ها", callback_data="manage_strategies")],
        [InlineKeyboardButton("✏️ تغییر نام دکمه‌ها", callback_data="rename_buttons_menu")],
        [InlineKeyboardButton("📉 بک‌تست استراتژی", callback_data="backtest_menu")],
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


# ============ کیبورد مدیریت استراتژی‌ها (پنل ادمین) ============
def strategy_list_keyboard():
    """لیست همه‌ی استراتژی‌های کشف‌شده رو نشون می‌ده."""
    from strategy_registry import get_all_strategies
    strategies = get_all_strategies()

    keyboard = []
    for strategy_id, module in strategies.items():
        name = module.STRATEGY_INFO.get("display_name", strategy_id)
        keyboard.append([InlineKeyboardButton(name, callback_data=f"strat_view_{strategy_id}")])

    keyboard.append([InlineKeyboardButton("➕ افزودن استراتژی جدید", callback_data="add_strategy_guide")])
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")])
    return InlineKeyboardMarkup(keyboard)


def strategy_params_keyboard(strategy_id):
    """پارامترهای یک استراتژی خاص رو با مقدار فعلی‌شون نشون می‌ده."""
    from strategy_registry import get_strategy
    from database import get_strategy_setting

    module = get_strategy(strategy_id)
    keyboard = []

    if module:
        params = module.STRATEGY_INFO.get("params", {})
        for param_name, param_def in params.items():
            current = get_strategy_setting(strategy_id, param_name, default=param_def["default"])
            label = f"{param_def['label']}: {current}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"strat_edit_{strategy_id}_{param_name}")])

        keyboard.append([InlineKeyboardButton("🔄 بازگشت به پیش‌فرض", callback_data=f"strat_reset_{strategy_id}")])

    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="manage_strategies")])
    return InlineKeyboardMarkup(keyboard)


# ============ کیبورد تغییر نام دکمه‌ها (پنل ادمین) ============
# ⚠️ این پنل جایگزین پنل قدیمی «مدیریت دکمه‌ها» شد که هم مخفی/نمایان
# کردن، هم تغییر اسم، هم بازگشت به پیش‌فرض رو با هم قاطی داشت. طبق
# تصمیم پروژه، الان این پنل فقط و فقط «تغییر اسم» دکمه‌های اصلی رو انجام
# می‌ده - ساده و بدون ابهام. قابلیت مخفی/نمایان‌کردن حذف شد.
def rename_buttons_keyboard(lang='fa'):
    """لیست همه‌ی دکمه‌های اصلی رو با اسم فعلی‌شون نشون می‌ده - کلیک روی هرکدام مستقیم رفتن به گرفتن اسم جدید."""
    from database import get_button_label

    keyboard = []
    for button_key, _, lang_key in MANAGEABLE_USER_BUTTONS:
        default_label = get_text(lang, lang_key)
        current_label = get_button_label(button_key, default_label)
        keyboard.append([InlineKeyboardButton(f"✏️ {current_label}", callback_data=f"btn_rename_{button_key}")])

    keyboard.append([InlineKeyboardButton("➕ افزودن دکمه‌ی سفارشی جدید", callback_data="add_custom_button")])

    # ===== دکمه‌های سفارشی موجود - فقط برای حذف (تغییر اسم برای این‌ها معنی نداره چون خودش قابل تعریفه) =====
    from database import get_all_custom_buttons
    for btn in get_all_custom_buttons():
        keyboard.append([InlineKeyboardButton(f"🗑️ حذف: {btn['label']}", callback_data=f"custom_delete_{btn['button_key']}")])

    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")])
    return InlineKeyboardMarkup(keyboard)


# ===== عملکردهای موجود ربات که یک دکمه‌ی سفارشی می‌تونه بهشون وصل بشه =====
LINKABLE_ACTIONS = [
    ("signal_menu", "🚨 دریافت سیگنال"),
    ("performance", "📊 عملکرد"),
    ("history", "📜 تاریخچه"),
    ("live_price", "💰 قیمت لحظه‌ای"),
    ("vip", "💎 VIP"),
    ("referral", "👥 رفرال"),
    ("settings", "⚙️ تنظیمات"),
    ("support", "🆘 پشتیبانی"),
]


def custom_button_type_keyboard():
    """انتخاب می‌کنه دکمه‌ی جدید متن ثابت نشون بده یا به یکی از عملکردهای موجود وصل بشه."""
    keyboard = [[InlineKeyboardButton("📝 متن ثابت (وقتی کلیک شد، یک پیام نشان بده)", callback_data="cbtype_text")]]
    for action_key, action_label in LINKABLE_ACTIONS:
        keyboard.append([InlineKeyboardButton(f"🔗 مثل: {action_label}", callback_data=f"cbtype_link_{action_key}")])
    return InlineKeyboardMarkup(keyboard)


# ============ کیبوردهای بک‌تست (پنل ادمین) ============
BACKTEST_SYMBOLS = {
    "gold": ("🥇 طلا (XAU/USD)", "XAU/USD"),
    "btc": ("₿ بیت‌کوین (BTC/USD)", "BTC/USD"),
}


def backtest_strategy_keyboard():
    """انتخاب استراتژی برای بک‌تست."""
    from strategy_registry import get_all_strategies
    strategies = get_all_strategies()

    keyboard = []
    for strategy_id, module in strategies.items():
        name = module.STRATEGY_INFO.get("display_name", strategy_id)
        keyboard.append([InlineKeyboardButton(name, callback_data=f"bt_strat_{strategy_id}")])

    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")])
    return InlineKeyboardMarkup(keyboard)


def backtest_symbol_keyboard(strategy_id):
    """انتخاب نماد (طلا یا بیت‌کوین) برای بک‌تست."""
    keyboard = []
    for symbol_key, (label, _) in BACKTEST_SYMBOLS.items():
        keyboard.append([InlineKeyboardButton(label, callback_data=f"bt_symbol_{strategy_id}_{symbol_key}")])
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="backtest_menu")])
    return InlineKeyboardMarkup(keyboard)


BACKTEST_MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def backtest_year_keyboard(which):
    """
    انتخاب سال شروع یا پایان بک‌تست (سال جاری و ۲ سال قبل).
    which: 'start' یا 'end'
    """
    from datetime import datetime
    current_year = datetime.now().year
    years = [current_year - 2, current_year - 1, current_year]

    keyboard = [[InlineKeyboardButton(str(y), callback_data=f"bty_{which}_{y}")] for y in years]
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="backtest_menu")])
    return InlineKeyboardMarkup(keyboard)


def backtest_month_keyboard(which, year):
    """
    انتخاب ماه شروع یا پایان بک‌تست، برای سال مشخص‌شده.
    which: 'start' یا 'end'
    """
    keyboard = []
    row = []
    for month_num, name in BACKTEST_MONTH_NAMES.items():
        row.append(InlineKeyboardButton(name, callback_data=f"btm_{which}_{year}_{month_num:02d}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="backtest_menu")])
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
        current_price = get_current_price(symbol)
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

    # ===== RR جدا برای هر مود (رفع باگ اشتراک RR بین Standard/Fast Scalp) =====
    rr_ratio = get_user_rr(user_id, mode=mode)

    reasons_text = "\n".join([f"• {r}" for r in analysis.get('reasons', ['دلیلی ثبت نشده'])])
    style = analysis.get('style', 'Surpri3e Strategy')
    strength = signal.get('strength', 'NORMAL')

    title_prefix = "⚠️ " if strength == "WEAK" else "🚨 "

    message = f"""
{title_prefix}**{get_text(lang, 'signal_title')}**

**💱 نماد:** {symbol}
**📊 {get_text(lang, 'style_label')}:** {style}
**📈 {get_text(lang, 'direction_label')}:** {'🟢 BUY' if signal['direction'] == 'BUY' else '🔴 SELL'}
**📍 {get_text(lang, 'entry_label')}:** {entry:.2f}
**🛑 {get_text(lang, 'sl_label')}:** {sl:.2f}
**🎯 {get_text(lang, 'tp_label')}:** {tp:.2f}
**🎯 {get_text(lang, 'rr_label')}:** 1:{rr_ratio:.1f}

**📝 {get_text(lang, 'reasons_label')}:**
{reasons_text}

⏱️ **{get_text(lang, 'timeframe_label')}:** {timeframe}
💰 **{get_text(lang, 'price_label')}:** {current_price:.2f}
🕐 **{get_text(lang, 'time_label')}:** {tehran_time.strftime('%Y-%m-%d %H:%M:%S')}

ℹ️ نتیجه‌ی این معامله (TP/SL) به‌صورت خودکار بررسی و اطلاع‌رسانی می‌شود.
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

        # سبک همیشه Surpri3e Strategy است - فقط باید حالت (Fast Scalp/Standard) انتخاب بشه
        context.user_data['style'] = 'surpri3e'
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET style=? WHERE id=?", ('surpri3e', user_id))
        conn.commit()
        conn.close()

        await query.edit_message_text(
            get_text(lang, 'select_mode'),
            reply_markup=mode_keyboard(lang),
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

    # ===== انتخاب حالت (Fast Scalp / Standard Mode) =====
    if data == "mode_fast_scalp":
        # Fast Scalp فقط روی تایم‌فریم 1 دقیقه کار می‌کنه - نیازی به انتخاب تایم‌فریم نیست
        context.user_data['timeframe'] = '1min'
        context.user_data['mode'] = 'fast_scalp'

        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            get_text(lang, 'select_rr'),
            reply_markup=rr_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    if data == "mode_standard":
        context.user_data['mode'] = 'standard'

        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            get_text(lang, 'select_timeframe'),
            reply_markup=timeframe_keyboard_standard(lang),
            parse_mode='Markdown'
        )
        return

    # ===== انتخاب تایم‌فریم (فقط برای Standard Mode) =====
    if data.startswith("tf_"):
        timeframe = data.replace("tf_", "")
        context.user_data['timeframe'] = timeframe

        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            get_text(lang, 'select_rr'),
            reply_markup=rr_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    # ===== انتخاب RR (اختصاصی همین کاربر و همین مود - رفع باگ اشتراک RR) =====
    if data.startswith("rr_"):
        rr = int(data.replace("rr_", ""))
        rr = max(1, min(10, rr))

        mode = context.user_data.get('mode', 'standard')
        set_user_rr(user_id, rr, mode=mode)  # ✅ per-user و per-mode، نه سراسری و نه مشترک بین مودها
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

        # ===== چک cooldown بر اساس تایم‌فریم =====
        # جلوگیری از درخواست‌های پشت‌سرهم روی کندلی که هنوز نبسته
        allowed, seconds_left = check_signal_cooldown(user_id, timeframe)
        if not allowed:
            minutes = seconds_left // 60
            seconds = seconds_left % 60
            wait_text = f"{minutes} دقیقه و {seconds} ثانیه" if minutes > 0 else f"{seconds} ثانیه"
            await query.edit_message_text(
                get_text(lang, 'signal_cooldown').format(wait=wait_text, timeframe=timeframe),
                reply_markup=user_keyboard(lang),
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

            # ===== مود فعلی کاربر (Standard یا Fast Scalp) - برای RR اختصاصی همون مود =====
            mode = context.user_data.get('mode', 'standard')
            user_rr = get_user_rr(user_id, mode=mode)

            while elapsed < MAX_WAIT_SECONDS:
                df = get_gold_candles(timeframe, symbol=symbol)

                if df is not None and not df.empty:
                    signal, analysis = create_signal(df, style, rr_override=user_rr)
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
                    live_price = get_current_price(symbol)
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

                    await send_signal(context.bot, user_id, trade_id, signal, analysis, df, timeframe, user_id, lang, symbol=symbol, current_price=live_price, mode=mode)
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
            price = get_current_price(symbol)
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
            get_text(lang, 'select_mode'),
            reply_markup=mode_keyboard(lang),
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
        rr_standard = get_user_rr(user_id, mode='standard')
        rr_scalp = get_user_rr(user_id, mode='fast_scalp')
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
                timeframe=settings.get('default_timeframe', '5min'),
                status='🟢 ' + get_text(lang, 'online') if settings.get('status', True) else '🔴 ' + get_text(lang, 'offline'),
                rr_standard=rr_standard,
                rr_scalp=rr_scalp,
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

    if data == "set_timeframe":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(
            "⏱️ **تایم‌فریم پیش‌فرض**\n\nگزینه‌ها: 1min, 5min, 15min, 1h, 4h, 1d",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'set_timeframe'
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
            f"👤 کاربر: `{req['user_id']}`\n"
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
            await query.edit_message_text("⚠️ این درخواست دیگر در انتظار نیست.", reply_markup=admin_keyboard())
            return

        set_user_vip_plan(req['user_id'], req['plan_id'])
        update_vip_payment_status(request_id, 'APPROVED')
        plan_label = VIP_PLANS.get(req['plan_id'], {}).get('label', req['plan_id'])

        await query.edit_message_text(f"✅ کاربر {req['user_id']} با پلن {plan_label} VIP شد.", reply_markup=admin_keyboard())

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
            await query.edit_message_text("⚠️ این درخواست دیگر در انتظار نیست.", reply_markup=admin_keyboard())
            return

        update_vip_payment_status(request_id, 'REJECTED')
        await query.edit_message_text(f"❌ درخواست #{request_id} رد شد.", reply_markup=admin_keyboard())

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

    # ===== مدیریت استراتژی‌ها =====
    if data == "manage_strategies":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(
            "⚙️ **مدیریت استراتژی‌ها**\n\nیک استراتژی را برای مشاهده و تنظیم پارامترهایش انتخاب کنید:",
            reply_markup=strategy_list_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data == "add_strategy_guide":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(
            "➕ **افزودن استراتژی جدید**\n\n"
            "افزودن یک استراتژی کاملاً جدید (مثلاً از یک اندیکاتور TradingView) "
            "به‌صورت خودکار از داخل ربات ممکن نیست، چون تبدیل کد Pine Script به "
            "پایتون نیاز به بازنویسی دستی منطق آن دارد.\n\n"
            "**برای افزودن استراتژی جدید:**\n"
            "۱. کد کامل اسکریپت Pine Script (TradingView) را برای توسعه‌دهنده ارسال کنید.\n"
            "۲. توسعه‌دهنده آن را به یک فایل پایتون استاندارد تبدیل کرده و در پوشه‌ی "
            "`strategies/` قرار می‌دهد.\n"
            "۳. پس از دیپلوی نسخه‌ی جدید، استراتژی به‌طور خودکار در همین لیست و در "
            "دکمه‌های ربات ظاهر می‌شود - بدون نیاز به هیچ تغییر دیگری.",
            reply_markup=strategy_list_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data.startswith("strat_view_"):
        if user_id != ADMIN_ID:
            return
        strategy_id = data.replace("strat_view_", "")

        from strategy_registry import get_strategy
        module = get_strategy(strategy_id)
        if not module:
            await query.edit_message_text("❌ استراتژی پیدا نشد.", reply_markup=strategy_list_keyboard())
            return

        info = module.STRATEGY_INFO
        text = f"⚙️ **{info['display_name']}**\n\n{info.get('description', '')}\n\nپارامتر مورد نظر برای تغییر را انتخاب کنید:"
        await query.edit_message_text(text, reply_markup=strategy_params_keyboard(strategy_id), parse_mode='Markdown')
        return

    if data.startswith("strat_edit_"):
        if user_id != ADMIN_ID:
            return
        # فرمت: strat_edit_{strategy_id}_{param_name}
        remainder = data.replace("strat_edit_", "")
        strategy_id, param_name = remainder.rsplit("_", 1)

        from strategy_registry import get_strategy
        module = get_strategy(strategy_id)
        if not module or param_name not in module.STRATEGY_INFO.get("params", {}):
            await query.edit_message_text("❌ پارامتر پیدا نشد.", reply_markup=strategy_list_keyboard())
            return

        param_def = module.STRATEGY_INFO["params"][param_name]
        await query.edit_message_text(
            f"⚙️ **{param_def['label']}**\n\n"
            f"{param_def.get('help', '')}\n\n"
            f"بازه‌ی مجاز: {param_def['min']} تا {param_def['max']}\n"
            f"مقدار پیش‌فرض: {param_def['default']}\n\n"
            f"مقدار جدید را وارد کنید:",
            reply_markup=strategy_params_keyboard(strategy_id),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'edit_strategy_param'
        context.user_data['edit_strategy_id'] = strategy_id
        context.user_data['edit_param_name'] = param_name
        return

    if data.startswith("strat_reset_"):
        if user_id != ADMIN_ID:
            return
        strategy_id = data.replace("strat_reset_", "")
        from database import reset_strategy_settings
        reset_strategy_settings(strategy_id)
        await query.edit_message_text(
            "🔄 **پارامترها به مقادیر پیش‌فرض بازگشتند.**",
            reply_markup=strategy_params_keyboard(strategy_id),
            parse_mode='Markdown'
        )
        return

    # ===== تغییر نام دکمه‌های شیشه‌ای =====
    if data == "rename_buttons_menu":
        if user_id != ADMIN_ID:
            return
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            "✏️ **تغییر نام دکمه‌ها**\n\nروی هر دکمه بزنید تا اسم جدیدش را وارد کنید:",
            reply_markup=rename_buttons_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    # ===== افزودن/مدیریت دکمه‌ی کاملاً سفارشی =====
    if data == "add_custom_button":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(
            "➕ **افزودن دکمه‌ی جدید**\n\n"
            "اسم دکمه (متنی که روی دکمه نوشته می‌شود) را بفرستید:",
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'add_custom_button_label'
        return

    if data == "cbtype_text":
        if user_id != ADMIN_ID:
            return
        label = context.user_data.get('new_custom_button_label')
        if not label:
            await query.edit_message_text("❌ **خطا: اسم دکمه پیدا نشد. دوباره از منو شروع کنید.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            return
        await query.edit_message_text(
            f"✅ اسم دکمه: «{label}»\n\nحالا متنی که با کلیک روی این دکمه به کاربر نمایش داده می‌شود را بفرستید:",
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'add_custom_button_text'
        return

    if data.startswith("cbtype_link_"):
        if user_id != ADMIN_ID:
            return
        action_key = data.replace("cbtype_link_", "")
        label = context.user_data.get('new_custom_button_label')

        if not label:
            await query.edit_message_text("❌ **خطا: اسم دکمه پیدا نشد. دوباره از منو شروع کنید.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            return

        import re
        import time
        slug = re.sub(r'[^a-zA-Z0-9_]', '', label.replace(' ', '_'))[:20] or "btn"
        button_key = f"{slug}_{int(time.time())}"

        from database import add_custom_button
        add_custom_button(button_key, label, response_text=None, link_action=action_key)

        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            f"✅ **دکمه‌ی «{label}» ساخته شد** و دقیقاً مثل دکمه‌ی «{dict(LINKABLE_ACTIONS).get(action_key, action_key)}» عمل می‌کند.\n\nاین دکمه در منوی اصلی کاربران ظاهر می‌شود.",
            reply_markup=rename_buttons_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    if data.startswith("custom_delete_"):
        if user_id != ADMIN_ID:
            return
        button_key = data.replace("custom_delete_", "")
        from database import delete_custom_button
        delete_custom_button(button_key)
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            "🗑️ **دکمه حذف شد.**",
            reply_markup=rename_buttons_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    if data.startswith("btn_rename_"):
        if user_id != ADMIN_ID:
            return
        button_key = data.replace("btn_rename_", "")
        await query.edit_message_text(
            f"✏️ **تغییر اسم دکمه**\n\nاسم جدید دکمه‌ی `{button_key}` را وارد کنید:",
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'rename_button'
        context.user_data['rename_button_key'] = button_key
        return

    # ===== بک‌تست =====
    if data == "backtest_menu":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(
            "📉 **بک‌تست استراتژی**\n\nابتدا استراتژی مورد نظر را انتخاب کنید:",
            reply_markup=backtest_strategy_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data.startswith("bt_strat_"):
        if user_id != ADMIN_ID:
            return
        strategy_id = data.replace("bt_strat_", "")
        context.user_data['backtest_strategy_id'] = strategy_id
        await query.edit_message_text(
            "💱 **نماد مورد نظر برای بک‌تست را انتخاب کنید:**",
            reply_markup=backtest_symbol_keyboard(strategy_id),
            parse_mode='Markdown'
        )
        return

    if data.startswith("bt_symbol_"):
        if user_id != ADMIN_ID:
            return
        # فرمت: bt_symbol_{strategy_id}_{symbol_key}
        remainder = data.replace("bt_symbol_", "")
        strategy_id, symbol_key = remainder.rsplit("_", 1)
        symbol_value = BACKTEST_SYMBOLS.get(symbol_key, ("", "XAU/USD"))[1]

        context.user_data['backtest_strategy_id'] = strategy_id
        context.user_data['backtest_symbol'] = symbol_value

        await query.edit_message_text(
            "📅 **سال شروع بک‌تست را انتخاب کنید:**",
            reply_markup=backtest_year_keyboard("start"),
            parse_mode='Markdown'
        )
        return

    if data.startswith("bty_"):
        if user_id != ADMIN_ID:
            return
        # فرمت: bty_{which}_{year}   which: start یا end
        remainder = data.replace("bty_", "")
        which, year = remainder.rsplit("_", 1)

        if which == "start":
            context.user_data['backtest_start_year'] = year
        else:
            context.user_data['backtest_end_year'] = year

        await query.edit_message_text(
            f"📅 **ماه {'شروع' if which == 'start' else 'پایان'} بک‌تست را انتخاب کنید ({year}):**",
            reply_markup=backtest_month_keyboard(which, year),
            parse_mode='Markdown'
        )
        return

    if data.startswith("btm_"):
        if user_id != ADMIN_ID:
            return
        # فرمت: btm_{which}_{year}_{month}
        remainder = data.replace("btm_", "")
        which, year, month = remainder.rsplit("_", 2)

        if which == "start":
            context.user_data['backtest_start_date'] = f"{year}-{month}-01"
            await query.edit_message_text(
                "📅 **سال پایان بک‌تست را انتخاب کنید:**",
                reply_markup=backtest_year_keyboard("end"),
                parse_mode='Markdown'
            )
            return

        # which == "end"
        import calendar
        last_day = calendar.monthrange(int(year), int(month))[1]
        end_date = f"{year}-{month}-{last_day:02d}"
        start_date = context.user_data.get('backtest_start_date')
        strategy_id = context.user_data.get('backtest_strategy_id')
        symbol = context.user_data.get('backtest_symbol', 'XAU/USD')

        if not start_date or not strategy_id:
            await query.edit_message_text(
                "❌ **خطا: اطلاعات بک‌تست ناقص است. دوباره از منو شروع کنید.**",
                reply_markup=admin_keyboard(),
                parse_mode='Markdown'
            )
            return

        from strategy_registry import get_strategy
        module = get_strategy(strategy_id)
        display_name = module.STRATEGY_INFO.get("display_name", strategy_id) if module else strategy_id

        await query.edit_message_text(
            f"⏳ **در حال اجرای بک‌تست...**\n\n💱 {symbol}\n📅 {start_date} تا {end_date}\n\nاین ممکن است چند دقیقه طول بکشد.",
            parse_mode='Markdown'
        )

        from backtest import run_backtest, format_backtest_report
        result = run_backtest(strategy_id, start_date, end_date, timeframe="1h", symbol=symbol)
        report_text = format_backtest_report(result, display_name)

        await query.message.reply_text(report_text, reply_markup=admin_keyboard(), parse_mode='Markdown')
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
        f"👤 کاربر: `{user_id}`\n"
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

        if action == 'set_timeframe':
            if text in ['1min', '5min', '15min', '1h', '4h', '1d']:
                result = set_default_timeframe(text)
                await update.message.reply_text(result, reply_markup=admin_keyboard(), parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ **گزینه نامعتبر!**\n1min, 5min, 15min, 1h, 4h, 1d", reply_markup=admin_keyboard(), parse_mode='Markdown')
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

        if action == 'edit_strategy_param':
            strategy_id = context.user_data.get('edit_strategy_id')
            param_name = context.user_data.get('edit_param_name')

            from strategy_registry import get_strategy
            from database import set_strategy_setting

            module = get_strategy(strategy_id) if strategy_id else None
            context.user_data['admin_action'] = None

            if not module or param_name not in module.STRATEGY_INFO.get("params", {}):
                await update.message.reply_text("❌ **خطا: استراتژی یا پارامتر پیدا نشد.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
                return

            param_def = module.STRATEGY_INFO["params"][param_name]
            try:
                value = float(text.replace(',', '.'))
                if param_def["type"] == "int":
                    value = int(value)

                if not (param_def["min"] <= value <= param_def["max"]):
                    await update.message.reply_text(
                        f"❌ **مقدار باید بین {param_def['min']} و {param_def['max']} باشد.**",
                        reply_markup=strategy_params_keyboard(strategy_id),
                        parse_mode='Markdown'
                    )
                    return

                set_strategy_setting(strategy_id, param_name, value)
                await update.message.reply_text(
                    f"✅ **{param_def['label']}** به مقدار **{value}** تغییر کرد.",
                    reply_markup=strategy_params_keyboard(strategy_id),
                    parse_mode='Markdown'
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ **لطفاً یک عدد معتبر وارد کنید.**",
                    reply_markup=strategy_params_keyboard(strategy_id),
                    parse_mode='Markdown'
                )
            return

        if action == 'rename_button':
            button_key = context.user_data.get('rename_button_key')
            context.user_data['admin_action'] = None
            lang = context.user_data.get('lang') or get_user_lang(user_id)

            if not button_key:
                await update.message.reply_text("❌ **خطا: دکمه پیدا نشد.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
                return

            from database import set_button_label
            set_button_label(button_key, text.strip())
            await update.message.reply_text(
                f"✅ **اسم دکمه به «{text.strip()}» تغییر کرد.**",
                reply_markup=rename_buttons_keyboard(lang),
                parse_mode='Markdown'
            )
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

        if action == 'add_custom_button_label':
            label = text.strip()
            if not label:
                await update.message.reply_text("❌ **اسم دکمه نمی‌تواند خالی باشد. دوباره وارد کنید:**", parse_mode='Markdown')
                return

            context.user_data['new_custom_button_label'] = label
            context.user_data['admin_action'] = None
            await update.message.reply_text(
                f"✅ اسم دکمه: «{label}»\n\nاین دکمه چه کاری انجام دهد؟",
                reply_markup=custom_button_type_keyboard(),
                parse_mode='Markdown'
            )
            return

        if action == 'add_custom_button_text':
            response_text = text.strip()
            label = context.user_data.get('new_custom_button_label')
            context.user_data['admin_action'] = None

            if not label:
                await update.message.reply_text("❌ **خطا: اسم دکمه پیدا نشد. دوباره از منو شروع کنید.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
                return

            if not response_text:
                await update.message.reply_text("❌ **متن پاسخ نمی‌تواند خالی باشد. دوباره وارد کنید:**", parse_mode='Markdown')
                context.user_data['admin_action'] = 'add_custom_button_text'
                return

            import re
            import time
            # ساخت یک شناسه‌ی یکتا از روی اسم دکمه + timestamp، برای جلوگیری از تداخل
            slug = re.sub(r'[^a-zA-Z0-9_]', '', label.replace(' ', '_'))[:20] or "btn"
            button_key = f"{slug}_{int(time.time())}"

            from database import add_custom_button
            add_custom_button(button_key, label, response_text)

            lang = context.user_data.get('lang') or get_user_lang(user_id)
            await update.message.reply_text(
                f"✅ **دکمه‌ی «{label}» ساخته شد و در منوی اصلی کاربران ظاهر می‌شود.**",
                reply_markup=rename_buttons_keyboard(lang),
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
