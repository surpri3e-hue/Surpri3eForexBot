import os

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
    update_result
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


TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 816822644


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


def signal_result_keyboard(trade_id):
    keyboard = [
        [
            InlineKeyboardButton("✅ TP HIT", callback_data=f"tp_{trade_id}"),
            InlineKeyboardButton("❌ SL HIT", callback_data=f"sl_{trade_id}")
        ],
        [InlineKeyboardButton("🚫 CANCEL", callback_data=f"cancel_{trade_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    add_user(user_id)
    update_activity(user_id)

    await update.message.reply_text(
        "🤖 Surpri3e AI Scanner\n\nبه پنل خوش آمدید",
        reply_markup=user_keyboard()
    )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ دسترسی ندارید")
        return

    await update.message.reply_text(
        "🤖 ADMIN PANEL\n\nمدیریت ربات:",
        reply_markup=admin_keyboard()
    )


# NOTE: button() must NOT be nested inside admin(). It's now a top-level
# function so CallbackQueryHandler(button) can actually see it.
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("tp_"):
        trade_id = data.split("_", 1)[1]
        update_result(trade_id, "TP")
        await query.edit_message_text("✅ TP ثبت شد")
        return

    if data.startswith("sl_"):
        trade_id = data.split("_", 1)[1]
        update_result(trade_id, "SL")
        await query.edit_message_text("❌ SL ثبت شد")
        return

    if data.startswith("cancel_"):
        await query.edit_message_text("🚫 سیگنال لغو شد")
        return

    if data == "back":
        await query.edit_message_text(
            "🤖 Surpri3e AI Scanner",
            reply_markup=user_keyboard()
        )
        return

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
            f"👥 USERS\n\nTotal Users:\n{get_users_count()}",
            reply_markup=admin_keyboard()
        )
        return

    if data == "analytics":
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
            f"🚀 SIGNAL CONTROL\n\nStatus:\n{status}",
            reply_markup=admin_keyboard()
        )
        return

    if data == "channel_lock":
        if query.from_user.id != ADMIN_ID:
            return
        status = toggle_channel_lock()
        await query.edit_message_text(
            f"🔒 CHANNEL LOCK\n\nStatus:\n{status}",
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

    if data == "performance":
        await query.edit_message_text(
            create_report(),
            reply_markup=user_keyboard()
        )
        return

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

            await query.message.reply_text(
                f"🚨 SIGNAL\n\n"
                f"💰 Gold Price Live Now:\n{df['close'].iloc[-1]}\n\n"
                f"Direction:\n{signal['direction']}\n\n"
                f"Entry:\n{signal['entry']}\n\n"
                f"SL:\n{signal['sl']}\n\n"
                f"TP:\n{signal['tp']}\n\n"
                f"Score:\n{signal.get('score', 0)}\n\n"
                f"👇 نتیجه معامله را انتخاب کنید:",
                reply_markup=signal_result_keyboard(trade_id)
            )
        else:
            await query.message.reply_text("❌ No Setup")

        return


# ================= TEXT =================

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

            await update.message.reply_text(
                f"🚨 SIGNAL\n\n"
                f"💰 Gold Price Live Now:\n{df['close'].iloc[-1]}\n\n"
                f"Direction:\n{signal['direction']}\n\n"
                f"Entry:\n{signal['entry']}\n\n"
                f"SL:\n{signal['sl']}\n\n"
                f"TP:\n{signal['tp']}\n\n"
                f"Score:\n{signal.get('score', 0)}\n\n"
                f"👇 نتیجه معامله را انتخاب کنید:",
                reply_markup=signal_result_keyboard(trade_id)
            )
        else:
            await update.message.reply_text("❌ No Setup")


# ================= RUN =================

def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not set. "
            "Set it before running the bot, e.g. export BOT_TOKEN=your_token_here"
        )

    init_settings()
    create_database()
    create_users_table()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

    print("🤖 Surpri3e AI Bot Started")
    app.run_polling()


if __name__ == "__main__":
    main()
