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

from market import get_current_price, get_gold_candles, get_tehran_time
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
    set_user_vip,
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
    get_user_winrate_stats
)

from settings import init_settings, get_settings
from admin_tools import (
    dashboard,
    toggle_signal,
    toggle_bot_lock,
    toggle_channel_lock,
    set_daily_signal_limit,
    set_rr_ratio,
    set_default_timeframe,
    set_referral_bonus,
    set_referral_threshold,
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
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN not set!")

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
def user_keyboard(lang='fa'):
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'signal_btn'), callback_data="signal_menu")],
        [
            InlineKeyboardButton(get_text(lang, 'performance_btn'), callback_data="performance"),
            InlineKeyboardButton(get_text(lang, 'history_btn'), callback_data="history")
        ],
        [
            InlineKeyboardButton(get_text(lang, 'price_btn'), callback_data="live_price"),
            InlineKeyboardButton(get_text(lang, 'vip_btn'), callback_data="vip")
        ],
        [
            InlineKeyboardButton(get_text(lang, 'referral_btn'), callback_data="referral"),
            InlineKeyboardButton(get_text(lang, 'settings_btn'), callback_data="settings")
        ],
        [
            InlineKeyboardButton(get_text(lang, 'support_btn'), callback_data="support"),
            InlineKeyboardButton("🌍 " + get_text(lang, 'change_lang'), callback_data="change_lang")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ============ کیبورد نتیجه سیگنال ============
def signal_result_keyboard(trade_id, lang='fa'):
    keyboard = [
        [
            InlineKeyboardButton(get_text(lang, 'tp_btn'), callback_data=f"tp_{trade_id}"),
            InlineKeyboardButton(get_text(lang, 'sl_btn'), callback_data=f"sl_{trade_id}")
        ],
        [InlineKeyboardButton(get_text(lang, 'cancel_btn'), callback_data=f"cancel_{trade_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ============ کیبورد ادمین ============
def admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")],
        [
            InlineKeyboardButton("👥 Users", callback_data="users"),
            InlineKeyboardButton("📈 Analytics", callback_data="analytics")
        ],
        [
            InlineKeyboardButton("📊 Set Daily Signal", callback_data="set_daily_signal"),
            InlineKeyboardButton("🎯 Set Default RR", callback_data="set_rr")
        ],
        [
            InlineKeyboardButton("⏱️ Set Timeframe", callback_data="set_timeframe"),
            InlineKeyboardButton("👥 Referral Bonus", callback_data="set_referral_bonus")
        ],
        [
            InlineKeyboardButton("🎯 Referral Threshold", callback_data="set_referral_threshold"),
            InlineKeyboardButton("🔄 Reset Signals", callback_data="reset_signals")
        ],
        [
            InlineKeyboardButton("🔒 Bot Lock", callback_data="bot_lock"),
            InlineKeyboardButton("🚀 Signal Control", callback_data="signal_control")
        ],
        [
            InlineKeyboardButton("🔒 Channel Lock", callback_data="channel_lock"),
            InlineKeyboardButton("👑 VIP User", callback_data="vip_user")
        ],
        [
            InlineKeyboardButton("🗑️ Delete User", callback_data="delete_user"),
            InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")
        ],
        [InlineKeyboardButton("📊 Reports", callback_data="reports")],
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


# ============ چک کردن عضویت در کانال ============
async def check_channel_membership(user_id, context):
    if not CHANNEL_ID:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.warning(f"خطا در بررسی عضویت کانال برای کاربر {user_id}: {e}")
        return False


# ============ ارسال سیگنال ============
async def send_signal(target, trade_id, signal, analysis, df, timeframe, user_id, lang='fa'):
    current_price = get_current_price()
    tehran_time = get_tehran_time()

    if not current_price:
        current_price = df['Close'].iloc[-1]

    # ===== RR اختصاصی همین کاربر، نه سراسری =====
    rr_ratio = get_user_rr(user_id)
    RISK = 5.0
    REWARD = RISK * rr_ratio

    if signal['direction'] == 'BUY':
        entry = round(current_price, 2)
        sl = round(current_price - RISK, 2)
        tp = round(current_price + REWARD, 2)
    else:
        entry = round(current_price, 2)
        sl = round(current_price + RISK, 2)
        tp = round(current_price - REWARD, 2)

    signal['entry'] = entry
    signal['sl'] = sl
    signal['tp'] = tp

    reasons_text = "\n".join([f"• {r}" for r in analysis.get('reasons', ['دلیلی ثبت نشده'])])
    style = analysis.get('style', 'ICT')
    strength = signal.get('strength', 'NORMAL')

    title_prefix = "⚠️ " if strength == "WEAK" else "🚨 "

    message = f"""
{title_prefix}**{get_text(lang, 'signal_title')}**

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

👇 {get_text(lang, 'result_label')}:
"""

    await target.reply_text(
        message,
        reply_markup=signal_result_keyboard(trade_id, lang),
        parse_mode='Markdown'
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

    if CHANNEL_ID:
        is_member = await check_channel_membership(user_id, context)
        if not is_member:
            await update.message.reply_text(
                f"🔒 برای استفاده از ربات باید عضو کانال ما شوید:\n\n📢 {CHANNEL_ID}\n\nپس از عضویت، دوباره /start را بزنید."
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

    # ===== انتخاب زبان =====
    if data.startswith("lang_"):
        lang = data.replace("lang_", "")
        context.user_data['lang'] = lang
        add_user(user_id, lang=lang)

        # سبک همیشه Surpri3e Strategy است - فقط باید حالت (Fast Scalp/Standard) انتخاب بشه
        context.user_data['style'] = 'SURPRI3E'
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET style=? WHERE id=?", ('SURPRI3E', user_id))
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

    # ===== انتخاب RR (اختصاصی همین کاربر) =====
    if data.startswith("rr_"):
        rr = int(data.replace("rr_", ""))
        rr = max(1, min(10, rr))

        set_user_rr(user_id, rr)  # ✅ per-user، نه سراسری
        context.user_data['rr'] = rr

        lang = context.user_data.get('lang') or get_user_lang(user_id)
        style = context.user_data.get('style') or get_user_style(user_id)
        timeframe = context.user_data.get('timeframe', '5min')

        signals_left = get_user_signals_left(user_id)
        if signals_left <= 0:
            await query.edit_message_text(
                get_text(lang, 'no_signals_left'),
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

            while elapsed < MAX_WAIT_SECONDS:
                df = get_gold_candles(timeframe)

                if df is not None and not df.empty:
                    signal, analysis = create_signal(df, style)
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
                    trade_id = save_trade(signal, user_id, style, strength)
                    use_signal(user_id)
                    record_signal_time(user_id, timeframe)  # ثبت زمان برای cooldown بعدی
                    await send_signal(query.message, trade_id, signal, analysis, df, timeframe, user_id, lang)
                else:
                    await query.message.reply_text(
                        get_text(lang, 'no_signal'),
                        reply_markup=user_keyboard(lang),
                        parse_mode='Markdown'
                    )
            else:
                await query.message.reply_text(
                    get_text(lang, 'error'),
                    reply_markup=user_keyboard(lang),
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.exception(f"خطا در تولید سیگنال برای کاربر {user_id}")
            await query.message.reply_text(
                f"❌ {get_text(lang, 'error')}: {str(e)}",
                reply_markup=user_keyboard(lang),
                parse_mode='Markdown'
            )
        return

    # ===== چک کردن قفل ربات =====
    if get_setting('bot_locked') == 'true' and user_id != ADMIN_ID:
        await query.edit_message_text("🔒 ربات قفل است.")
        return

    # ===== چک کردن عضویت در کانال =====
    if CHANNEL_ID and user_id != ADMIN_ID:
        is_member = await check_channel_membership(user_id, context)
        if not is_member:
            await query.edit_message_text(f"🔒 برای استفاده از ربات باید عضو کانال ما شوید:\n\n📢 {CHANNEL_ID}")
            return

    # ===== نتیجه سیگنال =====
    if data.startswith("tp_"):
        trade_id = data.split("_", 1)[1]
        update_result(trade_id, "TP")
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            get_text(lang, 'tp_registered'),
            reply_markup=user_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    if data.startswith("sl_"):
        trade_id = data.split("_", 1)[1]
        update_result(trade_id, "SL")
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            get_text(lang, 'sl_registered'),
            reply_markup=user_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    if data.startswith("cancel_"):
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        await query.edit_message_text(
            get_text(lang, 'canceled'),
            reply_markup=user_keyboard(lang),
            parse_mode='Markdown'
        )
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
        await query.edit_message_text(get_text(lang, 'fetching_price'), parse_mode='Markdown')

        try:
            price = get_current_price()
            tehran_time = get_tehran_time()

            if price:
                await query.edit_message_text(
                    get_text(lang, 'price_result').format(price=price, time=tehran_time.strftime('%H:%M:%S')),
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
        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="performance")]
        ])
        await query.edit_message_text(
            get_text(lang, 'weekly_performance_text').format(
                total=w['total'], wins=w['wins'], losses=w['losses'], winrate=w['winrate']
            ),
            reply_markup=back_keyboard,
            parse_mode='Markdown'
        )
        return

    # ===== عملکرد ماهانه =====
    if data == "perf_monthly":
        stats = get_user_winrate_stats(user_id)
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        m = stats['monthly']
        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(get_text(lang, 'back_btn'), callback_data="performance")]
        ])
        await query.edit_message_text(
            get_text(lang, 'monthly_performance_text').format(
                total=m['total'], wins=m['wins'], losses=m['losses'], winrate=m['winrate']
            ),
            reply_markup=back_keyboard,
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
            get_text(lang, 'vip_text'),
            reply_markup=user_keyboard(lang),
            parse_mode='Markdown'
        )
        return

    # ===== تنظیمات =====
    if data == "settings":
        settings = get_settings()
        lang = context.user_data.get('lang') or get_user_lang(user_id)
        rr = get_user_rr(user_id)
        style = context.user_data.get('style') or get_user_style(user_id)
        await query.edit_message_text(
            get_text(lang, 'settings_text').format(
                timeframe=settings.get('default_timeframe', '5min'),
                status='🟢 ' + get_text(lang, 'online') if settings.get('status', True) else '🔴 ' + get_text(lang, 'offline'),
                rr=rr,
                style=style,
                lang=lang
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

    if data == "set_rr":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(
            "🎯 **نسبت RR پیش‌فرض (برای کاربران جدید)**\n\nعدد را وارد کنید (مثلاً 2 برای 1:2):",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'set_rr'
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

    if data == "set_referral_bonus":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(
            "👥 **پاداش رفرال**\n\nچند سیگنال به ازای هر رفرال؟ (مثال: 1)",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'set_referral_bonus'
        return

    if data == "set_referral_threshold":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(
            "🎯 **آستانه رفرال**\n\nچند رفرال = افزایش سیگنال؟ (مثال: 5)",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'set_referral_threshold'
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
        await query.edit_message_text(f"🔒 **قفل کانال:** {status}", reply_markup=admin_keyboard(), parse_mode='Markdown')
        return

    # ===== مدیریت کاربران =====
    if data == "vip_user":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text(
            "👑 **VIP کردن کاربر**\n\nآیدی عددی کاربر را وارد کنید:",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['admin_action'] = 'vip_user'
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

        if action == 'set_daily_signal':
            if text.isdigit():
                result = set_daily_signal_limit(int(text))
                await update.message.reply_text(result, reply_markup=admin_keyboard(), parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ **لطفاً یک عدد وارد کنید.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            context.user_data['admin_action'] = None
            return

        if action == 'set_rr':
            try:
                value = float(text.replace(',', '.'))
                result = set_rr_ratio(value)
                await update.message.reply_text(result, reply_markup=admin_keyboard(), parse_mode='Markdown')
            except ValueError:
                await update.message.reply_text("❌ **لطفاً یک عدد معتبر وارد کنید.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
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

        if action == 'set_referral_bonus':
            if text.isdigit():
                result = set_referral_bonus(int(text))
                await update.message.reply_text(result, reply_markup=admin_keyboard(), parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ **لطفاً یک عدد وارد کنید.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            context.user_data['admin_action'] = None
            return

        if action == 'set_referral_threshold':
            if text.isdigit():
                result = set_referral_threshold(int(text))
                await update.message.reply_text(result, reply_markup=admin_keyboard(), parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ **لطفاً یک عدد وارد کنید.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            context.user_data['admin_action'] = None
            return

        if action == 'vip_user':
            if text.isdigit():
                set_user_vip(int(text), True)
                await update.message.reply_text(f"👑 **کاربر {text} VIP شد**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ **لطفاً آیدی عددی وارد کنید.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
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

        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("admin", admin))
        app.add_handler(CallbackQueryHandler(button))
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
