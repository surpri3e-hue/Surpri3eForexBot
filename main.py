import os
import logging
from datetime import datetime
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

from market import get_current_price
from signals import create_signal, ict_analysis_with_explanation
from ai_deepseek import analyze_with_deepseek

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
    toggle_ai,
    ai_status,
    logs_text,
    get_bot_settings,
    update_setting
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
        ],
        [InlineKeyboardButton("🤖 چت با AI", callback_data="ai_chat")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ کیبورد حالت چت AI ============
def ai_chat_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_from_ai")]
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
            InlineKeyboardButton("📈 Analytics", callback_data="analytics")
        ],
        [
            InlineKeyboardButton("🚀 Signal Control", callback_data="signal_control"),
            InlineKeyboardButton("🔒 Channel Lock", callback_data="channel_lock")
        ],
        [
            InlineKeyboardButton("🧠 AI Settings", callback_data="ai_settings"),
            InlineKeyboardButton("📜 Logs", callback_data="logs")
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"),
            InlineKeyboardButton("📊 Reports", callback_data="reports")
        ],
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

# ============ ارسال سیگنال با تحلیل ICT و دیپ سیک ============
async def send_signal_with_ai(target, trade_id, signal, analysis, df, timeframe):
    """ارسال سیگنال با تحلیل ICT و نظر دیپ سیک"""
    
    # ===== تحلیل ICT =====
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
    
    # ===== نظر دیپ سیک (اگه فعال باشه) =====
    settings = get_bot_settings()
    ai_enabled = settings.get('ai_enabled', 'true') == 'true'
    
    if ai_enabled:
        ai_text = f"""
🤖 **نظر دیپ سیک:**

{analyze_with_deepseek(df, signal, analysis)}
"""
    else:
        ai_text = """
🤖 **دیپ سیک:** غیرفعال (توسط ادمین)
"""
    
    # ===== ترکیب نهایی =====
    message = f"""
🚨 **سیگنال جدید**

{ict_text}

{ai_text}

⏱️ **تایم‌فریم:** {timeframe}
💰 **قیمت لحظه‌ای:** {df['Close'].iloc[-1]:.2f}
📡 **زمان:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
    add_user(user_id)
    update_activity(user_id)
    
    # خروج از حالت چت AI
    context.user_data['ai_chat_mode'] = False
    
    await update.message.reply_text(
        "🤖 **Surpri3e AI Scanner**\n\n"
        "به ربات سیگنال‌دهی طلا خوش آمدید!\n\n"
        "🔹 برای دریافت سیگنال روی دکمه 🚨 کلیک کنید\n"
        "🔹 تایم‌فریم مورد نظر را انتخاب کنید\n"
        "🔹 آمار عملکرد خود را در 📊 ببینید\n"
        "🔹 قیمت لحظه‌ای طلا را در 💰 ببینید\n"
        "🔹 با 🤖 چت با AI صحبت کنید\n"
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
        context.user_data['ai_chat_mode'] = False
        await query.edit_message_text(
            "🤖 **Surpri3e AI Scanner**\n\nبه پنل خوش آمدید",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== برگشت از چت AI =====
    if data == "back_from_ai":
        context.user_data['ai_chat_mode'] = False
        await query.edit_message_text(
            "🔙 **بازگشت به منو**\n\nبرای ادامه از دکمه‌های زیر استفاده کنید:",
            reply_markup=user_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== چت با AI =====
    if data == "ai_chat":
        context.user_data['ai_chat_mode'] = True
        await query.edit_message_text(
            "🤖 **حالت چت با AI فعال شد!**\n\n"
            "هر سوالی درباره طلا، ترید، تحلیل بازار یا هر موضوع دیگه‌ای داری، بپرس.\n\n"
            "💡 **پیشنهاد:**\n"
            "• طلا الان چطوره؟\n"
            "• تحلیل طلا امروز\n"
            "• آموزش ترید برای مبتدیان\n"
            "• حد ضرر چیه؟\n"
            "• استراتژی ICT چیه؟\n\n"
            "برای خروج از حالت چت، دکمه 🔙 بازگشت رو بزن.",
            reply_markup=ai_chat_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ===== قیمت لحظه‌ای =====
    if data == "live_price":
        await query.edit_message_text(
            "💰 **در حال دریافت قیمت لحظه‌ای...**",
            parse_mode='Markdown'
        )
        
        try:
            price = get_current_price()
            
            if price:
                await query.edit_message_text(
                    f"💰 **قیمت لحظه‌ای طلا**\n\n"
                    f"📊 **XAU/USD**\n\n"
                    f"💵 **قیمت:** {price:.2f} USD\n"
                    f"🕐 **آخرین بروزرسانی:** {datetime.now().strftime('%H:%M:%S')}\n\n"
                    f"برای دریافت سیگنال روی 🚨 کلیک کنید.",
                    reply_markup=user_keyboard(),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ **خطا در دریافت قیمت**\n\nلطفاً دوباره تلاش کنید.",
                    reply_markup=user_keyboard(),
                    parse_mode='Markdown'
                )
        except Exception as e:
            logging.error(f"Price error: {e}")
            await query.edit_message_text(
                "❌ **خطا در دریافت قیمت**",
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
            f"🔍 **در حال تحلیل طلا ({display_timeframe})...**",
            parse_mode='Markdown'
        )
        
        try:
            from market import get_gold_candles
            from signals import create_signal, ict_analysis_with_explanation
            
            df = get_gold_candles(timeframe)
            
            if df is not None and not df.empty:
                signal, analysis = ict_analysis_with_explanation(df)
                
                if signal:
                    trade_id = save_trade(signal)
                    await send_signal_with_ai(
                        query.message,
                        trade_id,
                        signal,
                        analysis,
                        df,
                        display_timeframe
                    )
                else:
                    await query.message.reply_text(
                        "❌ **سیگنالی پیدا نشد**\n\n"
                        "سعی کنید تایم‌فریم دیگری را انتخاب کنید.",
                        parse_mode='Markdown'
                    )
            else:
                await query.message.reply_text(
                    "❌ **خطا در دریافت داده**\n\n"
                    "لطفاً دوباره تلاش کنید.",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logging.error(f"Signal error: {e}")
            await query.message.reply_text(
                f"❌ **خطا:** {str(e)}",
                parse_mode='Markdown'
            )
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
            await query.edit_message_text(
                text,
                reply_markup=user_keyboard(),
                parse_mode='Markdown'
            )
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
        await query.edit_message_text(
            text,
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
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
        status = toggle_ai()
        await query.edit_message_text(
            f"🧠 **تنظیمات AI**\n\n**وضعیت:** {status}\n\n"
            f"• فعال/غیرفعال کردن دیپ سیک\n"
            f"• تنظیم تعداد درخواست‌ها\n"
            f"• مشاهده مصرف API",
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

    if data == "broadcast":
        if query.from_user.id != ADMIN_ID:
            return
        await query.edit_message_text(
            "📢 **ارسال همگانی**\n\n"
            "پیام خود را تایپ کنید.\n"
            "این پیام برای همه کاربران ارسال خواهد شد.\n\n"
            "⏹️ برای لغو، /cancel را بفرستید.",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['broadcast_mode'] = True
        return

    if data == "reports":
        if query.from_user.id != ADMIN_ID:
            return
        await query.edit_message_text(
            f"📊 **گزارشات**\n\n"
            f"📈 **گزارش روزانه:**\n{create_report()}\n\n"
            f"📊 **آمار کاربران:**\n• کل: {get_users_count()}\n"
            f"• فعال امروز: {get_active_users_today()}\n\n"
            f"📈 **آمار معاملات:**\n{get_statistics()}",
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
        return

# ============ مدیریت پیام‌های متنی ============
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_activity(user_id)
    
    text = update.message.text
    
    # ===== حالت چت با AI =====
    if context.user_data.get('ai_chat_mode', False):
        # چک کردن فعال بودن AI
        settings = get_bot_settings()
        ai_enabled = settings.get('ai_enabled', 'true') == 'true'
        
        if not ai_enabled:
            await update.message.reply_text(
                "⛔ **AI در حال حاضر غیرفعال است.**\n"
                "لطفاً بعداً تلاش کنید یا با ادمین تماس بگیرید.",
                parse_mode='Markdown'
            )
            return
        
        # ارسال به دیپ سیک
        await update.message.reply_text(
            "🤔 **در حال فکر کردن...**",
            parse_mode='Markdown'
        )
        
        try:
            # دریافت پاسخ از دیپ سیک
            response = await chat_with_deepseek(text)
            
            # ارسال پاسخ (با تقسیم به بخش‌های کوچک)
            if len(response) > 4000:
                parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for part in parts:
                    await update.message.reply_text(
                        part,
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    response,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logging.error(f"AI chat error: {e}")
            await update.message.reply_text(
                f"❌ **خطا در ارتباط با AI:** {str(e)}",
                parse_mode='Markdown'
            )
        return
    
    # ===== حالت ارسال همگانی =====
    if context.user_data.get('broadcast_mode', False):
        if update.effective_user.id == ADMIN_ID:
            if text.lower() == '/cancel':
                context.user_data['broadcast_mode'] = False
                await update.message.reply_text(
                    "⏹️ **ارسال همگانی لغو شد.**",
                    reply_markup=admin_keyboard(),
                    parse_mode='Markdown'
                )
                return
            
            # ارسال به همه کاربران
            users = get_all_users()
            success = 0
            fail = 0
            
            await update.message.reply_text(
                f"📤 **در حال ارسال به {len(users)} کاربر...**",
                parse_mode='Markdown'
            )
            
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user['id'],
                        text=f"📢 **پیام همگانی از ادمین:**\n\n{text}",
                        parse_mode='Markdown'
                    )
                    success += 1
                except:
                    fail += 1
            
            context.user_data['broadcast_mode'] = False
            
            await update.message.reply_text(
                f"✅ **ارسال همگانی انجام شد!**\n\n"
                f"✅ موفق: {success}\n"
                f"❌ ناموفق: {fail}",
                reply_markup=admin_keyboard(),
                parse_mode='Markdown'
            )
        return
    
    # ===== پیام معمولی =====
    await update.message.reply_text(
        "❌ **لطفاً از دکمه‌ها استفاده کنید!**\n\n"
        "برای دریافت سیگنال، روی دکمه 🚨 کلیک کنید.\n"
        "برای چت با AI، روی دکمه 🤖 چت با AI کلیک کنید.",
        parse_mode='Markdown'
    )

# ============ چت با دیپ سیک ============
async def chat_with_deepseek(question):
    """
    ارسال سوال به دیپ سیک و دریافت پاسخ
    """
    import requests
    import json
    
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    
    if not DEEPSEEK_API_KEY:
        return "⚠️ دیپ سیک فعال نیست. لطفاً API Key را تنظیم کنید."
    
    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "شما یک تحلیلگر حرفه‌ای بازارهای مالی با سبک ICT هستید. به زبان فارسی پاسخ دهید."},
                {"role": "user", "content": question}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"⚠️ خطا در ارتباط با دیپ سیک: {response.status_code}"
            
    except Exception as e:
        return f"⚠️ خطا: {str(e)}"

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
