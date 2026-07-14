import os
import logging
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

from market import get_gold_candles
from ict import ict_analysis
from signals import create_signal

from database import (
    create_database,
    save_trade,
    update_result,
    get_user_trades  # تابع جدید
)

from users import (
    create_users_table,
    add_user,
    update_activity,
    get_users_count
)

from settings import init_settings
from report import create_report

from admin_tools import (
    dashboard,
    toggle_signal,
    toggle_channel_lock,
    ai_status,
    logs_text
)

# ============ تنظیمات اولیه ============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 816822644

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable is not set!")

# ============ کیبورد کاربر ============
def user_keyboard():
    keyboard = [
        [InlineKeyboardButton("🚨 دریافت سیگنال", callback_data="signal")],
        [
            InlineKeyboardButton("📊 عملکرد", callback_data="performance"),
            InlineKeyboardButton("📜 تاریخچه", callback_data="history")
        ],
        [InlineKeyboardButton("💎 VIP", callback_data="vip")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")]
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
        [InlineKeyboardButton("🚀 Signal Control", callback_data="signal_control")],
        [InlineKeyboardButton("🔒 Channel Lock", callback_data="channel_lock")],
        [InlineKeyboardButton("🧠 AI Settings", callback_data="ai_settings")],
        [InlineKeyboardButton("📜 Logs", callback_data="logs")],
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

# ============ تابع ارسال سیگنال (برای جلوگیری از تکرار کد) ============
async def send_signal_message(target, trade_id, signal, df):
    """ارسال پیام سیگنال به کاربر"""
    message = (
        f"🚨 SIGNAL\n\n"
        f"💰 Gold Price: {df['close'].iloc[-1]}\n\n"
        f"Direction: {signal['direction']}\n"
        f"Entry: {signal['entry']}\n"
        f"SL: {signal['sl']}\n"
        f"TP: {signal['tp']}\n"
        f"Score: {signal.get('score', 0)}\n\n"
        f"👇 نتیجه معامله را انتخاب کنید:"
    )
    await target.reply_text(
        message,
        reply_markup=signal_result_keyboard(trade_id)
    )

# ============ دستور /start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    update_activity(user_id)
    
    await update.message.reply_text(
        "🤖 Surpri3e AI Scanner\n\nبه پنل خوش آمدید",
        reply_markup=user_keyboard()
    )

# ============ دستور /admin ============
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ دسترسی ندارید")
        return
    
    await update.message.reply_text(
        "🤖 ADMIN PANEL\n\nمدیریت ربات:",
        reply_markup=admin_keyboard()
    )

# ============ مدیریت دکمه‌ها ============
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # -------- دکمه‌های نتیجه سیگنال --------
    if data.startswith("tp_"):
        trade_id = data.split("_")[1]
        update_result(trade_id, "TP")
        await query.edit_message_text("✅ TP ثبت شد")
        return

    if data.startswith("sl_"):
        trade_id = data.split("_")[1]
        update_result(trade_id, "SL")
        await query.edit_message_text("❌ SL ثبت شد")
        return

    if data.startswith("cancel_"):
        await query.edit_message_text("🚫 سیگنال لغو شد")
        return

    # -------- دکمه برگشت --------
    if data == "back":
        await query.edit_message_text(
            "🤖 Surpri3e AI Scanner\n\nبه پنل خوش آمدید",
            reply_markup=user_keyboard()
        )
        return

    # -------- دکمه‌های کاربر --------
    if data == "signal":
        await query.edit_message_text("🔍 Analyzing XAUUSD...")
        
        df = get_gold_candles("5min")
        if df is None:
            await query.message.reply_text("❌ Data Error")
            return
        
        analysis = ict_analysis(df)
        signal = create_signal(df, analysis)
        
        if signal:
            trade_id = save_trade(signal)
            await send_signal_message(query.message, trade_id, signal, df)
        else:
            await query.message.reply_text("❌ No Setup")
        return

    if data == "performance":
        await query.edit_message_text(
            create_report(),
            reply_markup=user_keyboard()
        )
        return

    if data == "history":
        user_id = query.from_user.id
        trades = get_user_trades(user_id)
        
        if trades:
            text = "📜 **تاریخچه معاملات شما:**\n\n"
            for i, trade in enumerate(trades[:10], 1):
                result = trade.get('result', 'در انتظار')
                text += f"{i}. {trade['direction']} | Entry: {trade['entry']} | نتیجه: {result}\n"
            await query.edit_message_text(text, reply_markup=user_keyboard())
        else:
            await query.edit_message_text("📭 هنوز معامله‌ای ندارید!", reply_markup=user_keyboard())
        return

    if data == "vip":
        await query.edit_message_text(
            "💎 **پنل VIP**\n\n"
            "✅ دسترسی به سیگنال‌های ویژه\n"
            "✅ آنالیز پیشرفته\n"
            "✅ پشتیبانی اختصاصی\n\n"
            "برای عضویت با ادمین تماس بگیرید: @AmirHossein_Nik",
            reply_markup=user_keyboard()
        )
        return

    if data == "settings":
        await query.edit_message_text(
            "⚙️ **تنظیمات**\n\n"
            "🔹 تایم‌فریم: 5 دقیقه\n"
            "🔹 هشدار: فعال\n"
            "🔹 وضعیت: ربات آنلاین\n\n"
            "به زودی تنظیمات بیشتر اضافه میشه!",
            reply_markup=user_keyboard()
        )
        return

    # -------- پنل ادمین --------
    if data == "dashboard":
        if query.from_user.id != ADMIN_ID:
            return
        await query.edit_message_text(
            dashboard(),
            reply_markup=admin_keyboard()
        )
        return

    if data == "users":
        if query.from_user.id != ADMIN_ID:
            return
        await query.edit_message_text(
            f"👥 USERS\n\nTotal Users: {get_users_count()}",
            reply_markup=admin_keyboard()
        )
        return

    if data == "analytics":
        if query.from_user.id != ADMIN_ID:
            return
        await query.edit_message_text(
            create_report(),
            reply_markup=admin_keyboard()
        )
        return

    if data == "signal_control":
        if query.from_user.id != ADMIN_ID:
            return
        status = toggle_signal()
        await query.edit_message_text(
            f"🚀 SIGNAL CONTROL\n\nStatus: {status}",
            reply_markup=admin_keyboard()
        )
        return

    if data == "channel_lock":
        if query.from_user.id != ADMIN_ID:
            return
        status = toggle_channel_lock()
        await query.edit_message_text(
            f"🔒 CHANNEL LOCK\n\nStatus: {status}",
            reply_markup=admin_keyboard()
        )
        return

    if data == "ai_settings":
        if query.from_user.id != ADMIN_ID:
            return
        await query.edit_message_text(
            ai_status(),
            reply_markup=admin_keyboard()
        )
        return

    if data == "logs":
        if query.from_user.id != ADMIN_ID:
            return
        await query.edit_message_text(
            logs_text(),
            reply_markup=admin_keyboard()
        )
        return

# ============ مدیریت پیام‌های متنی ============
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_activity(user_id)
    text = update.message.text.upper()

    if text.startswith("SIGNAL"):
        df = get_gold_candles("5min")
        if df is None:
            await update.message.reply_text("❌ Data Error")
            return
        
        analysis = ict_analysis(df)
        signal = create_signal(df, analysis)
        
        if signal:
            trade_id = save_trade(signal)
            await send_signal_message(update.message, trade_id, signal, df)
        else:
            await update.message.reply_text("❌ No Setup")

# ============ اجرای اصلی ============
def main():
    # مقداردهی اولیه
    init_settings()
    create_database()
    create_users_table()
    
    # ساخت اپلیکیشن
    app = Application.builder().token(TOKEN).build()
    
    # اضافه کردن هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    
    print("🤖 Surpri3e AI Bot Started")
    
    # اجرا روی Railway با Webhook
    port = int(os.environ.get("PORT", 8080))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN')}/webhook"
    )

if __name__ == "__main__":
    main()
