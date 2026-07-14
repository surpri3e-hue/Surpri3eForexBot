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



# ---------- USER PANEL ----------

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
                "📊 وضعیت عملکرد",
                callback_data="status"
            )
        ],

        [
            InlineKeyboardButton(
                "📜 تاریخچه",
                callback_data="history"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 کانال",
                url="https://t.me/YOUR_CHANNEL"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)





# ---------- ADMIN PANEL ----------

def admin_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "👥 Users",
                callback_data="users"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 Report",
                callback_data="report"
            )
        ],

        [
            InlineKeyboardButton(
                "🧪 Test Signal",
                callback_data="signal"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)





async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    add_user(user_id)
    update_activity(user_id)


    await update.message.reply_text(
        """
🤖 Surpri3e AI Scanner

Welcome

Choose an option:
""",
        reply_markup=user_keyboard()
    )





async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id


    if user_id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ Access Denied"
        )

        return



    await update.message.reply_text(
        """
🤖 ADMIN PANEL

Select:
""",
        reply_markup=admin_keyboard()
    )






async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()


    data = query.data



    if data == "users":

        if query.from_user.id != ADMIN_ID:
            return


        count = get_users_count()


        await query.edit_message_text(
            f"""
👥 Users

Total:
{count}
"""
        )



    elif data == "report":


        await query.edit_message_text(
            create_report()
        )



    elif data == "status":


        await query.edit_message_text(
            create_report()
        )



    elif data == "signal":


        await query.edit_message_text(
            "🔍 Analyzing XAUUSD..."
        )


        df = get_gold_candles("5min")


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





async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message:

        update_activity(
            update.effective_user.id
        )



    text = update.message.text.upper()



    if text.startswith("SIGNAL"):

        df = get_gold_candles("5min")


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





# ---------- START ----------


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
