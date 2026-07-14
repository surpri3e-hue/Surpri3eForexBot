import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from market import get_gold_candles
from ict import ict_analysis
from signals import create_signal
from database import save_trade
from report import create_report

from users import (
    create_users_table,
    add_user,
    update_activity,
    get_users_count
)


TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 816822644



# ---------------- MENUS ----------------


def user_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "🚨 دریافت سیگنال",
                callback_data="signal"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 عملکرد",
                callback_data="performance"
            ),
            InlineKeyboardButton(
                "📜 تاریخچه",
                callback_data="history"
            )
        ],

        [
            InlineKeyboardButton(
                "💎 VIP",
                callback_data="vip"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 کانال",
                url="https://t.me/YOUR_CHANNEL"
            )
        ],

        [
            InlineKeyboardButton(
                "⚙️ تنظیمات",
                callback_data="settings"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)





def admin_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "📊 Dashboard",
                callback_data="dashboard"
            )
        ],

        [
            InlineKeyboardButton(
                "👥 Users",
                callback_data="users"
            ),
            InlineKeyboardButton(
                "📢 Broadcast",
                callback_data="broadcast"
            )
        ],

        [
            InlineKeyboardButton(
                "🔒 Channel Lock",
                callback_data="lock"
            )
        ],

        [
            InlineKeyboardButton(
                "🚀 Signal Control",
                callback_data="signal_control"
            )
        ],

        [
            InlineKeyboardButton(
                "📈 Analytics",
                callback_data="analytics"
            )
        ],

        [
            InlineKeyboardButton(
                "🧠 AI Settings",
                callback_data="ai_settings"
            )
        ],

        [
            InlineKeyboardButton(
                "📜 Logs",
                callback_data="logs"
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="back"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)





# ---------------- START ----------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    add_user(user_id)
    update_activity(user_id)


    await update.message.reply_text(
        """
🤖 Surpri3e AI Scanner

به پنل خوش آمدید

یک گزینه انتخاب کنید:
""",
        reply_markup=user_keyboard()
    )






async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ دسترسی ندارید"
        )

        return


    await update.message.reply_text(
        """
🤖 ADMIN PANEL

مدیریت ربات:
""",
        reply_markup=admin_keyboard()
    )





# ---------------- BUTTONS ----------------


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    data = query.data



    if data == "back":

        await query.edit_message_text(
            "🤖 Surpri3e AI Scanner",
            reply_markup=user_keyboard()
        )

        return




    if data == "users":

        if query.from_user.id != ADMIN_ID:
            return


        count = get_users_count()


        await query.edit_message_text(
            f"""
👥 Users

Total Users:
{count}
""",
            reply_markup=admin_keyboard()
        )

        return





    if data == "dashboard":

        await query.edit_message_text(
            """
📊 Dashboard

Bot: 🟢 Online

Market:
🟢 Connected

Scanner:
🟢 Active
""",
            reply_markup=admin_keyboard()
        )

        return






    if data in [
        "performance",
        "analytics"
    ]:


        await query.edit_message_text(
            create_report(),
            reply_markup=user_keyboard()
        )

        return






    if data == "signal":


        await query.edit_message_text(
            "🔍 Analyzing XAUUSD..."
        )


        df = get_gold_candles(
            "5min"
        )


        if df is None:

            await query.message.reply_text(
                "❌ Data Error"
            )

            return



        analysis = ict_analysis(df)


        signal = create_signal(
            df,
            analysis
        )



        if signal:

            save_trade(signal)


            await query.message.reply_text(
f"""
🚨 SIGNAL

Direction:
{signal['direction']}

Entry:
{signal['entry']}

SL:
{signal['sl']}

TP:
{signal['tp']}

Score:
{signal['score']}
"""
            )

        else:

            await query.message.reply_text(
                "❌ No Setup"
            )






    else:


        await query.edit_message_text(
            f"""
⚙️ بخش انتخابی:

{data}

به زودی فعال می‌شود.
""",
            reply_markup=admin_keyboard()
        )





# ---------------- TEXT ----------------


async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    update_activity(
        update.effective_user.id
    )


    text = update.message.text.upper()


    if text.startswith("SIGNAL"):


        df = get_gold_candles(
            "5min"
        )


        analysis = ict_analysis(df)


        signal = create_signal(
            df,
            analysis
        )



        if signal:

            save_trade(signal)


            await update.message.reply_text(
f"""
🚨 SIGNAL

Direction:
{signal['direction']}

Entry:
{signal['entry']}

SL:
{signal['sl']}

TP:
{signal['tp']}

Score:
{signal['score']}
"""
            )

        else:

            await update.message.reply_text(
                "❌ No Setup"
            )





# ---------------- RUN ----------------


create_users_table()


app = Application.builder().token(TOKEN).build()


app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


app.add_handler(
    CommandHandler(
        "admin",
        admin
    )
)


app.add_handler(
    CallbackQueryHandler(
        button
    )
)


app.add_handler(
    MessageHandler(
        filters.TEXT,
        handler
    )
)


app.run_polling()
