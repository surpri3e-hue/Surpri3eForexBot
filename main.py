import os
import logging
import io
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile
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
    get_statistics
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

# ============ کیبورد کاربر ============
def user_keyboard():
    keyboard = [
        [InlineKeyboardButton("🚨 دریافت سیگنال", callback_data="signal_menu")],
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

# ============ تابع تولید چارت ============
def generate_chart(df, signal, timeframe):
    """تولید چارت ساده با خطوط سیگنال"""
    try:
        df_copy = df.tail(30).copy()
        
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # رسم قیمت
        ax.plot(df_copy.index, df_copy['Close'], color='black', linewidth=1.5, label='Price')
        ax.fill_between(df_copy.index, df_copy['Close'].min() - 5, df_copy['Close'], 
                        alpha=0.2, color='blue')
        
        # خطوط سیگنال
        entry = signal['entry']
        sl = signal['sl']
        tp = signal['tp']
        
        ax.axhline(y=entry, color='blue', linestyle='--', linewidth=2, 
                   label=f'Entry: {entry:.2f}')
        ax.axhline(y=sl, color='red', linestyle='--', linewidth=2, 
                   label=f'SL: {sl:.2f}')
        ax.axhline(y=tp, color='green', linestyle='--', linewidth=2, 
                   label=f'TP: {tp:.2f}')
        
        # نواحی ریسک و ریوارد
        ax.axhspan(min(entry, sl), max(entry, sl), alpha=0.15, color='red', label='Risk')
        ax.axhspan(min(entry, tp), max(entry, tp), alpha=0.15, color='green', label='Reward')
        
        # تنظیمات
        ax.set_title(f'XAUUSD - {timeframe}', fontsize=14, fontweight='bold')
        ax.set_ylabel('Price (USD)', fontsize=12)
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # محاسبه RR
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = round(reward / risk, 2) if risk > 0 else 0
        
        direction = 'BUY' if signal['direction'] == 'BUY' else 'SELL'
        color = 'green' if direction == 'BUY' else 'red'
        
        info = f'Signal: {direction} | RR: 1:{rr} | Score: {signal.get("score", 0)}'
        ax.text(0.02, 0.98, info, transform=ax.transAxes,
                fontsize=11, fontweight='bold', color='white',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='black', alpha=0.8))
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close()
        
        return buf, rr
        
    except Exception as e:
        logging.error(f"Chart error: {e}")
        return None, 0

# ============ ارسال سیگنال با چارت ============
async def send_signal_with_chart(target, trade_id, signal, df, timeframe):
    chart_buf, rr = generate_chart(df, signal, timeframe)
    
    message = (
        f"🚨 **سیگنال جدید**\n\n"
        f"⏱️ **تایم‌فریم:** {timeframe}\n"
        f"💰 **قیمت فعلی:** {df['Close'].iloc[-1]:.2f}\n\n"
        f"📈 **جهت:** {'🟢 BUY' if signal['direction'] == 'BUY' else '🔴 SELL'}\n"
        f"📍 **ورود:** {signal['entry']:.2f}\n"
        f"🛑 **حد ضرر (SL):** {signal['sl']:.2f}\n"
        f"🎯 **حد سود (TP):** {signal['tp']:.2f}\n"
        f"⭐ **امتیاز:** {signal.get('score', 0)}\n"
        f"📊 **ریسک به ریوارد:** 1:{rr}\n\n"
        f"👇 نتیجه معامله را انتخاب کنید:"
    )
    
    if chart_buf:
        await target.reply_photo(
            photo=InputFile(chart_buf, filename="chart.png"),
            caption=message,
            reply_markup=signal_result_keyboard(trade_id),
            parse_mode='Markdown'
        )
    else:
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
    
    await update.message.reply_text(
        "🤖 **Surpri3e AI Scanner**\n\n"
        "به ربات سیگنال‌دهی طلا خوش آمدید!\n\n"
        "🔹 برای دریافت سیگنال روی دکمه 🚨 کلیک کنید\n"
        "🔹 تایم‌فریم مورد نظر را انتخاب کنید\n"
        "🔹 آمار عملکرد خود را در 📊 ببینید\n\n"
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
        "🤖 **پنل ادمین**\n\nمدیریت ربات:",
        reply_markup=admin_keyboard(),
        parse_mode='Markdown'
    )

# ============ مدیریت دکمه‌ها ============
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # نتیجه سیگنال
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

    # برگشت
    if data == "back":
        await query.edit_message_text(
            "🤖 **Surpri3e AI Scanner**\n\nبه پنل خوش آمدید",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    # منوی تایم‌فریم
    if data == "signal_menu":
        await query.edit_message_text(
            "⏱️ **انتخاب تایم‌فریم:**\n\nلطفاً تایم‌فریم مورد نظر را انتخاب کنید:",
            reply_markup=timeframe_keyboard(),
            parse_mode='Markdown'
        )
        return

    # انتخاب تایم‌فریم
    if data.startswith("tf_"):
        timeframe_map = {
            "tf_1min": "1min",
            "tf_5min": "5min",
            "tf_15min": "15min",
            "tf_1h": "1h",
            "tf_4h": "4h",
            "tf_1d": "1d"
        }
        
        timeframe = timeframe_map.get(data, "5min")
        display_timeframe = data.replace("tf_", "")
        
        await query.edit_message_text(
            f"🔍 **در حال تحلیل طلا ({display_timeframe})...**",
            parse_mode='Markdown'
        )
        
        try:
            df = get_gold_candles(timeframe)
            if df is None or df.empty:
                await query.message.reply_text("❌ **خطا در دریافت داده**", parse_mode='Markdown')
                return
            
            analysis = ict_analysis(df)
            signal = create_signal(df, analysis)
            
            if signal:
                trade_id = save_trade(signal)
                await send_signal_with_chart(query.message, trade_id, signal, df, display_timeframe)
            else:
                await query.message.reply_text("❌ **سیگنالی پیدا نشد**", parse_mode='Markdown')
                
        except Exception as e:
            logging.error(f"Signal error: {e}")
            await query.message.reply_text(f"❌ **خطا:** {str(e)}", parse_mode='Markdown')
        return

    # عملکرد
    if data == "performance":
        stats = get_statistics()
        await query.edit_message_text(
            f"📊 **آمار عملکرد**\n\n"
            f"📈 **کل معاملات:** {stats['total']}\n"
            f"✅ **برنده:** {stats['wins']}\n"
            f"❌ **بازنده:** {stats['losses']}\n"
            f"🎯 **نرخ موفقیت:** {stats['winrate']}%\n"
            f"💰 **فاکتور سود:** {stats['profit_factor']}",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    # تاریخچه
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

    # VIP
    if data == "vip":
        await query.edit_message_text(
            "💎 **پنل VIP**\n\n"
            "✅ **سیگنال‌های ویژه**\n"
            "✅ **آنالیز پیشرفته**\n"
            "✅ **پشتیبانی اختصاصی**\n\n"
            "برای عضویت با ادمین تماس بگیرید:\n👤 @AmirHossein_Nik",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    # تنظیمات
    if data == "settings":
        settings = get_settings()
        await query.edit_message_text(
            f"⚙️ **تنظیمات**\n\n"
            f"🔹 **تایم‌فریم پیش‌فرض:** {settings.get('default_timeframe', '5min')}\n"
            f"🔹 **هشدار:** {'فعال' if settings.get('alert', True) else 'غیرفعال'}\n"
            f"🔹 **وضعیت:** {'🟢 آنلاین' if settings.get('status', True) else '🔴 آفلاین'}\n"
            f"🔹 **ارسال چارت:** {'فعال' if settings.get('send_chart', True) else 'غیرفعال'}\n\n"
            "تنظیمات بیشتر به زودی اضافه میشه!",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== پنل ادمین =====
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
        await query.edit_message_text(
            f"📈 **تحلیل پیشرفته**\n\n"
            f"📊 **کل معاملات:** {stats['total']}\n"
            f"✅ **برنده:** {stats['wins']}\n"
            f"❌ **بازنده:** {stats['losses']}\n"
            f"🎯 **نرخ موفقیت:** {stats['winrate']}%\n"
            f"💰 **فاکتور سود:** {stats['profit_factor']}",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
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

# ============ پیام‌های متنی ============
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_activity(user_id)
    
    await update.message.reply_text(
        "❌ **لطفاً از دکمه‌ها استفاده کنید!**\n\nبرای دریافت سیگنال، روی دکمه 🚨 کلیک کنید.",
        parse_mode='Markdown'
    )

# ============ اجرای اصلی ============
def main():
    try:
        init_settings()
        create_database()
        create_users_table()
        
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
