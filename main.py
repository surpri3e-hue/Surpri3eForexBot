import os
import logging
from datetime import datetime, timedelta
import pytz
import threading
import time
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
from signals import create_signal, ict_analysis_with_explanation

from database import (
    create_database,
    save_trade,
    update_result,
    get_user_trades,
    get_statistics,
    get_setting,
    update_setting
)

from users import (
    create_users_table,
    add_user,
    update_activity,
    get_users_count,
    get_all_users,
    get_user_detail,
    set_user_vip,
    delete_user,
    reset_daily_signals,
    get_user_signals_left,
    use_signal,
    add_referral
)

from settings import init_settings, get_settings
from report import create_report

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
    report,
    get_today_stats
)

# ============ تنظیمات اولیه ============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 816822644))
SUPPORT_ID = "@RealSurprise"
CHANNEL_ID = os.getenv("CHANNEL_ID")  # مثلاً @MyChannel

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN not set!")

TEHRAN_TZ = pytz.timezone('Asia/Tehran')

# ============ کیبورد کاربر ============
def user_keyboard():
    keyboard = [
        [InlineKeyboardButton("🚨 دریافت سیگنال", callback_data="signal_menu")],
        [
            InlineKeyboardButton("📊 عملکرد", callback_data="performance"),
            InlineKeyboardButton("📜 تاریخچه", callback_data="history")
        ],
        [
            InlineKeyboardButton("💰 قیمت لحظه‌ای", callback_data="live_price"),
            InlineKeyboardButton("💎 VIP", callback_data="vip")
        ],
        [
            InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"),
            InlineKeyboardButton("🆘 پشتیبانی", callback_data="support")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ کیبورد انتخاب تایم‌فریم ============
def timeframe_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("1 دقیقه", callback_data="tf_1min"),
            InlineKeyboardButton("5 دقیقه", callback_data="tf_5min"),
            InlineKeyboardButton("15 دقیقه", callback_data="tf_15min")
        ],
        [
            InlineKeyboardButton("1 ساعت", callback_data="tf_1h"),
            InlineKeyboardButton("4 ساعت", callback_data="tf_4h"),
            InlineKeyboardButton("1 روز", callback_data="tf_1d")
        ],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ کیبورد ادمین ============
def admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")],
        [
            InlineKeyboardButton("👥 Users", callback_data="users"),
            InKeyboardButton("📈 Analytics", callback_data="analytics")
        ],
        [
            InlineKeyboardButton("📊 Set Daily Signal", callback_data="set_daily_signal"),
            InlineKeyboardButton("🎯 Set RR Ratio", callback_data="set_rr")
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

# ============ کیبورد نتیجه سیگنال ============
def signal_result_keyboard(trade_id):
    keyboard = [
        [
            InlineKeyboardButton("✅ TP HIT", callback_data=f"tp_{trade_id}"),
            InlineKeyboardButton("❌ SL HIT", callback_data=f"sl_{trade_id}")
        ],
        [InlineKeyboardButton("🚫 CANCEL", callback_data=f"cancel_{trade_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ چک کردن عضویت در کانال ============
async def check_channel_membership(user_id, context):
    if not CHANNEL_ID:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ============ ارسال سیگنال ============
async def send_signal(target, trade_id, signal, analysis, df, timeframe):
    current_price = get_current_price()
    tehran_time = get_tehran_time()
    
    ict_text = f"""
📊 **تحلیل ICT:**

**جهت:** {'🟢 BUY' if signal['direction'] == 'BUY' else '🔴 SELL'}
**ورود:** {signal['entry']:.2f}
**حد ضرر:** {signal['sl']:.2f}
**حد سود:** {signal['tp']:.2f}

**دلایل:**
{chr(10).join([f"• {r}" for r in analysis.get('reasons', ['دلیلی ثبت نشده'])])}

**امتیاز:** {analysis.get('score', 0)}
"""

    message = f"""
🚨 **سیگنال جدید**

{ict_text}

⏱️ **تایم‌فریم:** {timeframe}
💰 **قیمت لحظه‌ای:** {current_price if current_price else df['Close'].iloc[-1]:.2f}
🕐 **زمان تهران:** {tehran_time.strftime('%Y-%m-%d %H:%M:%S')}

👇 نتیجه معامله را انتخاب کنید:
"""

    await target.reply_text(
        message,
        reply_markup=signal_result_keyboard(trade_id),
        parse_mode='Markdown'
    )

# ============ دستور /start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # ===== چک کردن قفل ربات =====
    if get_setting('bot_locked') == 'true':
        await update.message.reply_text("🔒 **ربات در حال حاضر قفل است.**\nلطفاً بعداً تلاش کنید.")
        return
    
    # ===== چک کردن عضویت در کانال =====
    if CHANNEL_ID:
        is_member = await check_channel_membership(user_id, context)
        if not is_member:
            await update.message.reply_text(
                f"🔒 **برای استفاده از ربات باید عضو کانال ما شوید:**\n\n"
                f"📢 {CHANNEL_ID}\n\n"
                f"پس از عضویت، دوباره /start را بزنید."
            )
            return
    
    add_user(user_id)
    update_activity(user_id)
    context.user_data['admin_action'] = None

    await update.message.reply_text(
        "🤖 **Surpri3e AI Scanner**\n\n"
        "به ربات سیگنال‌دهی طلا خوش آمدید!\n\n"
        "🔹 برای دریافت سیگنال روی دکمه 🚨 کلیک کنید\n"
        "🔹 تایم‌فریم مورد نظر را انتخاب کنید\n"
        "🔹 آمار عملکرد خود را در 📊 ببینید\n"
        "🔹 قیمت لحظه‌ای طلا را در 💰 ببینید\n"
        "🔹 برای ارتباط با پشتیبانی روی 🆘 کلیک کنید\n\n"
        "موفق باشید! 🍀",
        reply_markup=user_keyboard(),
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

    # ===== چک کردن قفل ربات =====
    if get_setting('bot_locked') == 'true' and user_id != ADMIN_ID:
        await query.edit_message_text("🔒 **ربات قفل است.**")
        return

    # ===== چک کردن عضویت در کانال =====
    if CHANNEL_ID and user_id != ADMIN_ID:
        is_member = await check_channel_membership(user_id, context)
        if not is_member:
            await query.edit_message_text(
                f"🔒 **برای استفاده از ربات باید عضو کانال ما شوید:**\n\n📢 {CHANNEL_ID}"
            )
            return

    # ===== نتیجه سیگنال =====
    if data.startswith("tp_"):
        trade_id = data.split("_")[1]
        update_result(trade_id, "TP")
        await query.edit_message_text(
            "✅ **TP ثبت شد**\n\nبرای ادامه از دکمه‌های زیر استفاده کنید:",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data.startswith("sl_"):
        trade_id = data.split("_")[1]
        update_result(trade_id, "SL")
        await query.edit_message_text(
            "❌ **SL ثبت شد**\n\nبرای ادامه از دکمه‌های زیر استفاده کنید:",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data.startswith("cancel_"):
        await query.edit_message_text(
            "🚫 **سیگنال لغو شد**\n\nبرای ادامه از دکمه‌های زیر استفاده کنید:",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== برگشت =====
    if data == "back":
        context.user_data['admin_action'] = None
        await query.edit_message_text(
            "🤖 **Surpri3e AI Scanner**\n\nبه پنل خوش آمدید",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== قیمت لحظه‌ای =====
    if data == "live_price":
        await query.edit_message_text("💰 **در حال دریافت قیمت...**", parse_mode='Markdown')

        try:
            price = get_current_price()
            tehran_time = get_tehran_time()
            
            if price:
                await query.edit_message_text(
                    f"💰 **قیمت لحظه‌ای طلا**\n\n"
                    f"📊 **XAU/USD**\n\n"
                    f"💵 **قیمت:** {price:.2f} USD\n"
                    f"🕐 **زمان تهران:** {tehran_time.strftime('%H:%M:%S')}",
                    reply_markup=user_keyboard(),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ **خطا در دریافت قیمت**",
                    reply_markup=user_keyboard(),
                    parse_mode='Markdown'
                )
        except Exception as e:
            await query.edit_message_text(
                f"❌ **خطا:** {str(e)}",
                reply_markup=user_keyboard(),
                parse_mode='Markdown'
            )
        return

    # ===== پشتیبانی =====
    if data == "support":
        await query.edit_message_text(
            f"🆘 **پشتیبانی**\n\n"
            f"👤 **ایدی:** {SUPPORT_ID}\n"
            f"📱 [تماس با پشتیبانی](https://t.me/RealSurprise)\n\n"
            f"⏰ **ساعت پاسخگویی:** ۲۴ ساعته",
            reply_markup=user_keyboard(),
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        return

    # ===== منوی تایم‌فریم =====
    if data == "signal_menu":
        await query.edit_message_text(
            "⏱️ **انتخاب تایم‌فریم:**",
            reply_markup=timeframe_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== انتخاب تایم‌فریم =====
    if data.startswith("tf_"):
        # چک کردن فعال بودن سیگنال
        if get_setting('signal_enabled') != 'true':
            await query.message.reply_text("⛔ **سیگنال‌دهی غیرفعال است.**", parse_mode='Markdown')
            return

        timeframe_map = {
            "tf_1min": "1min", "tf_5min": "5min", "tf_15min": "15min",
            "tf_1h": "1h", "tf_4h": "4h", "tf_1d": "1d"
        }
        timeframe = timeframe_map.get(data, "5min")
        display = data.replace("tf_", "")

        # ===== چک کردن تعداد سیگنال باقی‌مانده =====
        signals_left = get_user_signals_left(user_id)
        if signals_left <= 0:
            await query.message.reply_text(
                "❌ **تعداد سیگنال روزانه شما تمام شده!**\n"
                "صبر کنید تا فردا یا از طریق رفرال افزایش دهید.",
                parse_mode='Markdown'
            )
            return

        await query.edit_message_text(f"🔍 **در حال تحلیل ({display})...**", parse_mode='Markdown')

        try:
            df = get_gold_candles(timeframe)
            if df is not None and not df.empty:
                signal, analysis = ict_analysis_with_explanation(df)

                if signal:
                    trade_id = save_trade(signal, user_id)
                    use_signal(user_id)
                    await send_signal(query.message, trade_id, signal, analysis, df, display)
                else:
                    await query.message.reply_text("❌ **سیگنالی پیدا نشد**", parse_mode='Markdown')
            else:
                await query.message.reply_text("❌ **خطا در دریافت داده**", parse_mode='Markdown')

        except Exception as e:
            await query.message.reply_text(f"❌ **خطا:** {str(e)}", parse_mode='Markdown')
        return

    # ===== عملکرد =====
    if data == "performance":
        stats = get_statistics()
        signals_left = get_user_signals_left(user_id)
        await query.edit_message_text(
            f"📊 **آمار عملکرد**\n\n"
            f"📈 **کل معاملات:** {stats['total']}\n"
            f"✅ **برنده:** {stats['wins']}\n"
            f"❌ **بازنده:** {stats['losses']}\n"
            f"🎯 **نرخ موفقیت:** {stats['winrate']}%\n\n"
            f"📊 **سیگنال باقی‌مانده امروز:** {signals_left}",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== تاریخچه =====
    if data == "history":
        trades = get_user_trades(user_id)
        if trades:
            text = "📜 **تاریخچه معاملات:**\n\n"
            for i, t in enumerate(trades[:10], 1):
                emoji = "✅" if t['result'] == "TP" else "❌" if t['result'] == "SL" else "⏳"
                text += f"{i}. {t['direction']} | {t['entry']} | {emoji} {t['result']}\n"
            await query.edit_message_text(text, reply_markup=user_keyboard(), parse_mode='Markdown')
        else:
            await query.edit_message_text("📭 **هنوز معامله‌ای ندارید!**", reply_markup=user_keyboard(), parse_mode='Markdown')
        return

    # ===== VIP =====
    if data == "vip":
        await query.edit_message_text(
            "💎 **پنل VIP**\n\n"
            "✅ **سیگنال‌های ویژه**\n"
            "✅ **آنالیز پیشرفته**\n"
            "✅ **پشتیبانی اختصاصی**\n\n"
            "👤 @RealSurprise",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== تنظیمات =====
    if data == "settings":
        settings = get_settings()
        await query.edit_message_text(
            f"⚙️ **تنظیمات**\n\n"
            f"🔹 **تایم‌فریم:** {settings.get('default_timeframe', '5min')}\n"
            f"🔹 **وضعیت:** {'🟢 آنلاین' if settings.get('status', True) else '🔴 آفلاین'}\n"
            f"🔹 **RR:** 1:2 (ثابت)",
            reply_markup=user_keyboard(),
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
            text += f"🆔 {u['id']} | {'👑 VIP' if u['is_vip'] else '👤 عادی'} | {u['referral_count']} رفرال\n"
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
            "🎯 **نسبت RR**\n\nعدد را وارد کنید (مثلاً 2 برای 1:2):",
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
            "📢 **ارسال همگانی**\n\nپیام خود را تایپ کنید:",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['broadcast_mode'] = True
        return

    if data == "reports":
        if user_id != ADMIN_ID:
            return
        stats = get_statistics()
        today_stats = get_today_stats()
        users = get_users_count()
        await query.edit_message_text(
            f"📊 **گزارش کامل**\n\n"
            f"👥 **کل کاربران:** {users}\n"
            f"📈 **کل معاملات:** {stats['total']}\n"
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

# ============ مدیریت پیام‌ها ============
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_activity(user_id)
    text = update.message.text

    # ===== ارسال همگانی =====
    if context.user_data.get('broadcast_mode', False):
        if user_id == ADMIN_ID:
            if text.lower() == '/cancel':
                context.user_data['broadcast_mode'] = False
                await update.message.reply_text("⏹️ **لغو شد.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
                return

            users = get_all_users()
            success = 0
            for u in users:
                try:
                    await context.bot.send_message(
                        chat_id=u['id'],
                        text=f"{text}"
                    )
                    success += 1
                except:
                    pass

            context.user_data['broadcast_mode'] = False
            await update.message.reply_text(
                f"✅ **ارسال شد!**\n\n✅ موفق: {success}\n❌ ناموفق: {len(users) - success}",
                reply_markup=admin_keyboard(),
                parse_mode='Markdown'
            )
        return

    # ===== ورودی‌های ادمین =====
    if context.user_data.get('admin_action'):
        action = context.user_data['admin_action']
        
        if action == 'set_daily_signal':
            if text.isdigit():
                set_daily_signal_limit(int(text))
                await update.message.reply_text(f"✅ **تعداد سیگنال روزانه: {text}**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ **لطفاً یک عدد وارد کنید.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            context.user_data['admin_action'] = None
            return

        if action == 'set_rr':
            if text.isdigit():
                set_rr_ratio(int(text))
                await update.message.reply_text(f"✅ **نسبت RR: 1:{text}**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ **لطفاً یک عدد وارد کنید.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            context.user_data['admin_action'] = None
            return

        if action == 'set_timeframe':
            if text in ['1min', '5min', '15min', '1h', '4h', '1d']:
                set_default_timeframe(text)
                await update.message.reply_text(f"✅ **تایم‌فریم پیش‌فرض: {text}**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ **گزینه نامعتبر!**\n1min, 5min, 15min, 1h, 4h, 1d", reply_markup=admin_keyboard(), parse_mode='Markdown')
            context.user_data['admin_action'] = None
            return

        if action == 'set_referral_bonus':
            if text.isdigit():
                set_referral_bonus(int(text))
                await update.message.reply_text(f"✅ **پاداش هر رفرال: {text} سیگنال**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ **لطفاً یک عدد وارد کنید.**", reply_markup=admin_keyboard(), parse_mode='Markdown')
            context.user_data['admin_action'] = None
            return

        if action == 'set_referral_threshold':
            if text.isdigit():
                set_referral_threshold(int(text))
                await update.message.reply_text(f"✅ **آستانه رفرال: {text}**", reply_markup=admin_keyboard(), parse_mode='Markdown')
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

    await update.message.reply_text(
        "❌ **لطفاً از دکمه‌ها استفاده کنید!**",
        reply_markup=user_keyboard(),
        parse_mode='Markdown'
    )

# ============ تابع ریست شبانه ============
def reset_daily():
    while True:
        now = datetime.now(TEHRAN_TZ)
        target = now.replace(hour=3, minute=30, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        time.sleep(wait_seconds)
        reset_daily_signals()
        logging.info("🔄 سیگنال‌های روزانه ریست شد.")

# ============ اجرا ============
def main():
    try:
        init_settings()
        create_database()
        create_users_table()

        # ===== ریست شبانه =====
        threading.Thread(target=reset_daily, daemon=True).start()

        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("admin", admin))
        app.add_handler(CallbackQueryHandler(button))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

        logging.info("🤖 Surpri3e AI Bot Started")
        print("✅ Surpri3e AI Bot Started")

        port = int(os.environ.get("PORT", 8080))
        print(f"🔄 Running on port {port}")
        app.run_polling()

    except Exception as e:
        logging.error(f"❌ Main Error: {e}")
        print(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    main()
