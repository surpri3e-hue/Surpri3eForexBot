import os
import logging
import io
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
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

from market import get_gold_candles, get_current_price
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
SUPPORT_ID = "@RealSurprise"

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
        [
            InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"),
            InlineKeyboardButton("🆘 پشتیبانی", callback_data="support")
        ]
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

# ============ تابع تولید چارت مثل تریدینگ ویو ============
def generate_chart_tradingview(df, signal, timeframe):
    """
    تولید چارت شبیه تریدینگ ویو با کندل‌های حرفه‌ای
    """
    try:
        # 30 کندل آخر
        df_copy = df.tail(40).copy()
        
        # تنظیمات
        plt.style.use('dark_background')
        fig = plt.figure(figsize=(16, 10), facecolor='#131722')
        
        # تقسیم صفحه
        gs = fig.add_gridspec(2, 1, height_ratios=[3.5, 1], hspace=0)
        ax1 = fig.add_subplot(gs[0], facecolor='#131722')
        ax2 = fig.add_subplot(gs[1], sharex=ax1, facecolor='#131722')
        
        # ===== کندل‌ها =====
        width = 0.6
        body_width = 0.8
        wick_width = 0.05
        
        # جداسازی کندل‌های صعودی و نزولی
        up = df_copy[df_copy['Close'] >= df_copy['Open']]
        down = df_copy[df_copy['Close'] < df_copy['Open']]
        
        # ===== کندل‌های صعودی (سبز) =====
        if not up.empty:
            # بدنه
            ax1.bar(up.index, up['Close'] - up['Open'], body_width, 
                    bottom=up['Open'], color='#26a69a', edgecolor='#26a69a', linewidth=0.5)
            # فتیله بالا
            ax1.bar(up.index, up['High'] - up['Close'], wick_width, 
                    bottom=up['Close'], color='#26a69a', linewidth=0.5)
            # فتیله پایین
            ax1.bar(up.index, up['Low'] - up['Open'], wick_width, 
                    bottom=up['Open'], color='#26a69a', linewidth=0.5)
        
        # ===== کندل‌های نزولی (قرمز) =====
        if not down.empty:
            # بدنه
            ax1.bar(down.index, down['Close'] - down['Open'], body_width, 
                    bottom=down['Open'], color='#ef5350', edgecolor='#ef5350', linewidth=0.5)
            # فتیله بالا
            ax1.bar(down.index, down['High'] - down['Open'], wick_width, 
                    bottom=down['Open'], color='#ef5350', linewidth=0.5)
            # فتیله پایین
            ax1.bar(down.index, down['Low'] - down['Close'], wick_width, 
                    bottom=down['Close'], color='#ef5350', linewidth=0.5)
        
        # ===== خطوط سیگنال =====
        entry = signal['entry']
        
        # محاسبه SL و TP با نسبت 1:2
        if signal['direction'] == 'BUY':
            sl = round(entry - 5, 2)
            tp = round(entry + 10, 2)
        else:
            sl = round(entry + 5, 2)
            tp = round(entry - 10, 2)
        
        signal['sl'] = sl
        signal['tp'] = tp
        
        # ===== کشیدن خطوط =====
        # خط Entry
        ax1.axhline(y=entry, color='#2962ff', linestyle='--', linewidth=2, 
                   alpha=0.9, zorder=10)
        ax1.text(df_copy.index[-1], entry, f' Entry {entry:.2f}', 
                color='#2962ff', fontsize=10, fontweight='bold',
                verticalalignment='bottom', horizontalalignment='right')
        
        # خط SL
        ax1.axhline(y=sl, color='#ff1744', linestyle='--', linewidth=2, 
                   alpha=0.9, zorder=10)
        ax1.text(df_copy.index[-1], sl, f' SL {sl:.2f}', 
                color='#ff1744', fontsize=10, fontweight='bold',
                verticalalignment='top', horizontalalignment='right')
        
        # خط TP
        ax1.axhline(y=tp, color='#00e676', linestyle='--', linewidth=2, 
                   alpha=0.9, zorder=10)
        ax1.text(df_copy.index[-1], tp, f' TP {tp:.2f}', 
                color='#00e676', fontsize=10, fontweight='bold',
                verticalalignment='bottom', horizontalalignment='right')
        
        # ===== نواحی =====
        ax1.axhspan(min(entry, sl), max(entry, sl), alpha=0.1, color='red', zorder=0)
        ax1.axhspan(min(entry, tp), max(entry, tp), alpha=0.1, color='green', zorder=0)
        
        # ===== تنظیمات محور اول =====
        ax1.set_title(f'XAUUSD - {timeframe}', fontsize=16, fontweight='bold', 
                      color='white', pad=10)
        ax1.set_ylabel('Price', fontsize=11, color='#787b86')
        ax1.tick_params(colors='#787b86', labelsize=9)
        ax1.grid(True, alpha=0.1, color='#2a2e39', linestyle='-')
        ax1.set_facecolor('#131722')
        
        # ===== محاسبه قیمت‌های بالا و پایین =====
        high_price = df_copy['High'].max()
        low_price = df_copy['Low'].min()
        price_range = high_price - low_price
        
        # تنظیم محدوده قیمت
        ax1.set_ylim(low_price - price_range * 0.08, high_price + price_range * 0.08)
        
        # ===== نمایش قیمت بالا و پایین =====
        ax1.text(0.02, 0.98, f'H: {high_price:.2f}', transform=ax1.transAxes,
                color='#787b86', fontsize=9, verticalalignment='top')
        ax1.text(0.02, 0.02, f'L: {low_price:.2f}', transform=ax1.transAxes,
                color='#787b86', fontsize=9, verticalalignment='bottom')
        
        # ===== نمایش قیمت فعلی =====
        current = df_copy['Close'].iloc[-1]
        ax1.text(0.98, 0.02, f'{current:.2f}', transform=ax1.transAxes,
                color='white', fontsize=12, fontweight='bold',
                horizontalalignment='right', verticalalignment='bottom',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#2962ff', alpha=0.8))
        
        # ===== محاسبه RR =====
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = round(reward / risk, 2) if risk > 0 else 2.0
        
        direction = 'BUY' if signal['direction'] == 'BUY' else 'SELL'
        dir_color = '#26a69a' if direction == 'BUY' else '#ef5350'
        
        # ===== نمایش اطلاعات =====
        info_text = f'{direction}  |  RR 1:{rr}  |  Score {signal.get("score", 0)}'
        ax1.text(0.5, 0.98, info_text, transform=ax1.transAxes,
                color='white', fontsize=12, fontweight='bold',
                horizontalalignment='center', verticalalignment='top',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#2a2e39', alpha=0.8))
        
        # ===== حجم =====
        colors = ['#26a69a' if df_copy['Close'].iloc[i] >= df_copy['Open'].iloc[i] else '#ef5350' 
                  for i in range(len(df_copy))]
        ax2.bar(df_copy.index, df_copy['Volume'], color=colors, alpha=0.7, width=0.7)
        ax2.set_ylabel('Volume', fontsize=11, color='#787b86')
        ax2.tick_params(colors='#787b86', labelsize=9)
        ax2.grid(True, alpha=0.1, color='#2a2e39', linestyle='-')
        ax2.set_facecolor('#131722')
        
        # مخفی کردن x-axis
        plt.setp(ax1.get_xticklabels(), visible=False)
        
        # ===== ذخیره =====
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', 
                    facecolor='#131722', edgecolor='none')
        buf.seek(0)
        plt.close('all')
        
        return buf
        
    except Exception as e:
        logging.error(f"Chart error: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============ ارسال سیگنال با چارت ============
async def send_signal_with_chart(target, trade_id, signal, df, timeframe):
    chart_buf = generate_chart_tradingview(df, signal, timeframe)
    
    current_price = get_current_price()
    
    message = (
        f"🚨 **سیگنال جدید**\n\n"
        f"⏱️ **تایم‌فریم:** {timeframe}\n"
        f"💰 **قیمت لحظه‌ای:** {current_price if current_price else df['Close'].iloc[-1]:.2f}\n\n"
        f"📈 **جهت:** {'🟢 BUY' if signal['direction'] == 'BUY' else '🔴 SELL'}\n"
        f"📍 **ورود:** {signal['entry']:.2f}\n"
        f"🛑 **حد ضرر (SL):** {signal['sl']:.2f}\n"
        f"🎯 **حد سود (TP):** {signal['tp']:.2f}\n"
        f"⭐ **امتیاز:** {signal.get('score', 0)}\n"
        f"📊 **ریسک به ریوارد:** 1:2 (ثابت)\n"
        f"📡 **منبع:** {signal.get('source', 'ICT')}\n\n"
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
        "🔹 آمار عملکرد خود را در 📊 ببینید\n"
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
        "🤖 **پنل ادمین**\n\nمدیریت ربات:",
        reply_markup=admin_keyboard(),
        parse_mode='Markdown'
    )

# ============ مدیریت دکمه‌ها ============
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

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
        await query.edit_message_text(
            "🤖 **Surpri3e AI Scanner**\n\nبه پنل خوش آمدید",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== پشتیبانی =====
    if data == "support":
        await query.edit_message_text(
            f"🆘 **پشتیبانی**\n\n"
            f"برای ارتباط با پشتیبانی روی لینک زیر کلیک کنید:\n\n"
            f"👤 **ایدی پشتیبانی:** {SUPPORT_ID}\n\n"
            f"📱 **لینک مستقیم:**\n"
            f"[تماس با پشتیبانی](https://t.me/RealSurprise)\n\n"
            f"⏰ **ساعت پاسخگویی:** ۲۴ ساعته",
            reply_markup=user_keyboard(),
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        return

    # ===== منوی تایم‌فریم =====
    if data == "signal_menu":
        await query.edit_message_text(
            "⏱️ **انتخاب تایم‌فریم:**\n\nلطفاً تایم‌فریم مورد نظر را انتخاب کنید:",
            reply_markup=timeframe_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== انتخاب تایم‌فریم =====
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
            f"🔍 **در حال دریافت قیمت لحظه‌ای و سیگنال...**",
            parse_mode='Markdown'
        )
        
        try:
            current_price = get_current_price()
            df = get_gold_candles(timeframe)
            
            analysis = ict_analysis(df) if df is not None else None
            signal = create_signal(df, analysis)
            
            if signal:
                if current_price:
                    signal['entry'] = round(current_price, 2)
                
                trade_id = save_trade(signal)
                
                if df is not None and not df.empty:
                    await send_signal_with_chart(query.message, trade_id, signal, df, display_timeframe)
                else:
                    message = (
                        f"🚨 **سیگنال جدید**\n\n"
                        f"💰 **قیمت لحظه‌ای:** {current_price if current_price else 'N/A'}\n"
                        f"📈 **جهت:** {'🟢 BUY' if signal['direction'] == 'BUY' else '🔴 SELL'}\n"
                        f"📍 **ورود:** {signal['entry']:.2f}\n"
                        f"🛑 **حد ضرر (SL):** {signal['sl']:.2f}\n"
                        f"🎯 **حد سود (TP):** {signal['tp']:.2f}\n"
                        f"⭐ **امتیاز:** {signal.get('score', 0)}\n"
                        f"📊 **ریسک به ریوارد:** 1:2 (ثابت)\n"
                        f"📡 **منبع:** {signal.get('source', 'ICT')}\n\n"
                        f"👇 نتیجه معامله را انتخاب کنید:"
                    )
                    await query.message.reply_text(
                        message,
                        reply_markup=signal_result_keyboard(trade_id),
                        parse_mode='Markdown'
                    )
            else:
                await query.message.reply_text("❌ **سیگنالی پیدا نشد**", parse_mode='Markdown')
                
        except Exception as e:
            logging.error(f"Signal error: {e}")
            await query.message.reply_text(f"❌ **خطا:** {str(e)}", parse_mode='Markdown')
        return

    # ===== عملکرد =====
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

    # ===== تاریخچه =====
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

    # ===== VIP =====
    if data == "vip":
        await query.edit_message_text(
            "💎 **پنل VIP**\n\n"
            "✅ **سیگنال‌های ویژه**\n"
            "✅ **آنالیز پیشرفته**\n"
            "✅ **پشتیبانی اختصاصی**\n\n"
            "برای عضویت با ادمین تماس بگیرید:\n👤 @RealSurprise",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== تنظیمات =====
    if data == "settings":
        settings = get_settings()
        await query.edit_message_text(
            f"⚙️ **تنظیمات**\n\n"
            f"🔹 **تایم‌فریم پیش‌فرض:** {settings.get('default_timeframe', '5min')}\n"
            f"🔹 **هشدار:** {'فعال' if settings.get('alert', True) else 'غیرفعال'}\n"
            f"🔹 **وضعیت:** {'🟢 آنلاین' if settings.get('status', True) else '🔴 آفلاین'}\n"
            f"🔹 **ارسال چارت:** {'فعال' if settings.get('send_chart', True) else 'غیرفعال'}\n"
            f"🔹 **نسبت RR:** 1:2 (ثابت)\n\n"
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
