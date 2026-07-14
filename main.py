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
    get_user_trades,
    get_statistics,
    get_open_trades
)

from users import (
    create_users_table,
    add_user,
    update_activity,
    get_users_count,
    get_all_users
)

from settings import init_settings, get_settings
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
ADMIN_ID = int(os.getenv("ADMIN_ID", 816822644))

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN not set!")

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

# ============ ارسال سیگنال ============
async def send_signal(target, trade_id, signal, df):
    message = (
        f"🚨 **سیگنال جدید**\n\n"
        f"💰 **قیمت طلا:** {df['close'].iloc[-1]:.2f}\n\n"
        f"📈 **جهت:** {signal['direction']}\n"
        f"📍 **ورود:** {signal['entry']:.2f}\n"
        f"🛑 **حد ضرر:** {signal['sl']:.2f}\n"
        f"🎯 **حد سود:** {signal['tp']:.2f}\n"
        f"⭐ **امتیاز:** {signal.get('score', 0)}\n\n"
        f"👇 نتیجه معامله را انتخاب کنید:"
    )
    await target.reply_text(
        message,
        reply_markup=signal_result_keyboard(trade_id),
        parse_mode='Markdown'
    )

# ============ دستور /start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    update_activity(user_id)
    
    welcome = (
        "🤖 **Surpri3e AI Scanner**\n\n"
        "به ربات سیگنال‌دهی طلا خوش آمدید!\n\n"
        "🔹 برای دریافت سیگنال روی دکمه 🚨 کلیک کنید\n"
        "🔹 آمار عملکرد خود را در 📊 ببینید\n"
        "🔹 تاریخچه معاملات در 📜 موجود است\n\n"
        "موفق باشید! 🍀"
    )
    
    await update.message.reply_text(
        welcome,
        reply_markup=user_keyboard(),
        parse_mode='Markdown'
    )

# ============ دستور /admin ============
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ دسترسی ندارید!")
        return
    
    await update.message.reply_text(
        "🤖 **پنل ادمین**\n\nمدیریت ربات:",
        reply_markup=admin_keyboard(),
        parse_mode='Markdown'
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
        await query.edit_message_text("✅ **TP ثبت شد**", parse_mode='Markdown')
        return

    if data.startswith("sl_"):
        trade_id = data.split("_")[1]
        update_result(trade_id, "SL")
        await query.edit_message_text("❌ **SL ثبت شد**", parse_mode='Markdown')
        return

    if data.startswith("cancel_"):
        await query.edit_message_text("🚫 **سیگنال لغو شد**", parse_mode='Markdown')
        return

    # -------- دکمه برگشت --------
    if data == "back":
        await query.edit_message_text(
            "🤖 **Surpri3e AI Scanner**\n\nبه پنل خوش آمدید",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    # -------- دکمه‌های کاربر --------
    if data == "signal":
        await query.edit_message_text("🔍 **در حال تحلیل طلا...**", parse_mode='Markdown')
        
        try:
            df = get_gold_candles("5min")
            if df is None or df.empty:
                await query.message.reply_text("❌ **خطا در دریافت داده**", parse_mode='Markdown')
                return
            
            analysis = ict_analysis(df)
            signal = create_signal(df, analysis)
            
            if signal:
                trade_id = save_trade(signal)
                await send_signal(query.message, trade_id, signal, df)
            else:
                await query.message.reply_text("❌ **سیگنالی پیدا نشد**", parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Signal error: {e}")
            await query.message.reply_text(f"❌ **خطا:** {str(e)}", parse_mode='Markdown')
        return

    if data == "performance":
        stats = get_statistics()
        text = (
            f"📊 **آمار عملکرد**\n\n"
            f"📈 **کل معاملات:** {stats['total']}\n"
            f"✅ **برنده:** {stats['wins']}\n"
            f"❌ **بازنده:** {stats['losses']}\n"
            f"🎯 **نرخ موفقیت:** {stats['winrate']}%\n"
            f"💰 **فاکتور سود:** {stats['profit_factor']}\n"
        )
        await query.edit_message_text(text, reply_markup=user_keyboard(), parse_mode='Markdown')
        return

    if data == "history":
        trades = get_user_trades()
        
        if trades:
            text = "📜 **تاریخچه معاملات:**\n\n"
            for i, trade in enumerate(trades[:10], 1):
                result = trade.get('result', 'در انتظار')
                emoji = "✅" if result == "TP" else "❌" if result == "SL" else "⏳"
                text += f"{i}. {trade['direction']} | ورود: {trade['entry']} | {emoji} {result}\n"
            await query.edit_message_text(text, reply_markup=user_keyboard(), parse_mode='Markdown')
        else:
            await query.edit_message_text(
                "📭 **هنوز معامله‌ای ندارید!**",
                reply_markup=user_keyboard(),
                parse_mode='Markdown'
            )
        return

    if data == "vip":
        text = (
            "💎 **پنل VIP**\n\n"
            "✅ **سیگنال‌های ویژه**\n"
            "✅ **آنالیز پیشرفته**\n"
            "✅ **پشتیبانی اختصاصی**\n\n"
            "برای عضویت با ادمین تماس بگیرید:\n"
            "👤 @AmirHossein_Nik"
        )
        await query.edit_message_text(text, reply_markup=user_keyboard(), parse_mode='Markdown')
        return

    if data == "settings":
        settings = get_settings()
        text = (
            "⚙️ **تنظیمات**\n\n"
            f"🔹 **تایم‌فریم:** {settings.get('timeframe', '5min')}\n"
            f"🔹 **هشدار:** {'فعال' if settings.get('alert', True) else 'غیرفعال'}\n"
            f"🔹 **وضعیت:** {'🟢 آنلاین' if settings.get('status', True) else '🔴 آفلاین'}\n\n"
            "تنظیمات بیشتر به زودی اضافه میشه!"
        )
        await query.edit_message_text(text, reply_markup=user_keyboard(), parse_mode='Markdown')
        return

    # -------- پنل ادمین --------
    if data == "dashboard":
        if query.from_user.id != ADMIN_ID:
            return
        await query.edit_message_text(
            dashboard(),
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data == "users":
        if query.from_user.id != ADMIN_ID:
            return
        users = get_all_users()
        text = f"👥 **کاربران**\n\n**کل کاربران:** {len(users)}\n\n"
        for user in users[:20]:
            text += f"🆔 {user['id']} | فعال: {user['last_active']}\n"
        await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode='Markdown')
        return

    if data == "analytics":
        if query.from_user.id != ADMIN_ID:
            return
        stats = get_statistics()
        text = (
            f"📈 **تحلیل پیشرفته**\n\n"
            f"📊 **کل معاملات:** {stats['total']}\n"
            f"✅ **برنده:** {stats['wins']}\n"
            f"❌ **بازنده:** {stats['losses']}\n"
            f"🎯 **نرخ موفقیت:** {stats['winrate']}%\n"
            f"💰 **فاکتور سود:** {stats['profit_factor']}\n"
            f"📈 **سود کل:** {stats.get('total_profit', 0)}\n"
        )
        await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode='Markdown')
        return

    if data == "signal_control":
        if query.from_user.id != ADMIN_ID:
            return
        status = toggle_signal()
        await query.edit_message_text(
            f"🚀 **کنترل سیگنال**\n\n**وضعیت:** {status}",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data == "channel_lock":
        if query.from_user.id != ADMIN_ID:
            return
        status = toggle_channel_lock()
        await query.edit_message_text(
            f"🔒 **قفل کانال**\n\n**وضعیت:** {status}",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data == "ai_settings":
        if query.from_user.id != ADMIN_ID:
            return
        await query.edit_message_text(
            ai_status(),
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data == "logs":
        if query.from_user.id != ADMIN_ID:
            return
        await query.edit_message_text(
            logs_text(),
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        return

# ============ مدیریت پیام‌های متنی ============
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_activity(user_id)
    text = update.message.text.upper()

    if text.startswith("SIGNAL") or text == "سیگنال":
        await update.message.reply_text("🔍 **در حال تحلیل...**", parse_mode='Markdown')
        
        try:
            df = get_gold_candles("5min")
            if df is None or df.empty:
                await update.message.reply_text("❌ **خطا در دریافت داده**", parse_mode='Markdown')
                return
            
            analysis = ict_analysis(df)
            signal = create_signal(df, analysis)
            
            if signal:
                trade_id = save_trade(signal)
                await send_signal(update.message, trade_id, signal, df)
            else:
                await update.message.reply_text("❌ **سیگنالی پیدا نشد**", parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Handler error: {e}")
            await update.message.reply_text(f"❌ **خطا:** {str(e)}", parse_mode='Markdown')

# ============ اجرای اصلی ============
def main():
    try:
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
        
        logging.info("🤖 Surpri3e AI Bot Started")
        print("🤖 Surpri3e AI Bot Started")
        
        # اجرا با Polling (ساده‌ترین روش)
        port = int(os.environ.get("PORT", 8080))
        print(f"🔄 Running on port {port}")
        app.run_polling()
        
    except Exception as e:
        logging.error(f"Main error: {e}")
        print(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    main()
