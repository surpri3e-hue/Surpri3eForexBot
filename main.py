import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

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
    save_trade,
    create_database
)

from report import create_report

from users import (
    create_users_table,
    add_user,
    update_activity,
    get_users_count
)

from settings import (
    init_settings,
    get_setting,
    set_setting
)

from admin_tools import (
    dashboard,
    toggle_signal
)



TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 816822644





# ================= USER MENU =================


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
        ]

    ]

    return InlineKeyboardMarkup(keyboard)





# ================= ADMIN MENU =================


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
                "📈 Analytics",
                callback_data="analytics"
            )
        ],

        [
            InlineKeyboardButton(
                "🔒 Channel Lock",
                callback_data="channel_lock"
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
                "🧠 AI Settings",
                callback_data="ai_settings"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 Broadcast",
                callback_data="broadcast"
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
    # ================= START =================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    add_user(user_id)
    update_activity(user_id)


    await update.message.reply_text(
        """
🤖 Surpri3e AI Scanner

به پنل خوش آمدید
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
""",
        reply_markup=admin_keyboard()
    )





# ================= SIGNAL =================


async def send_signal(update):

    df = get_gold_candles(
        "5min"
    )


    if df is None:

        await update.message.reply_text(
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





# ================= BUTTON HANDLER =================


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





    if query.from_user.id == ADMIN_ID:



        if data == "dashboard":

            await query.edit_message_text(
                dashboard(),
                reply_markup=admin_keyboard()
            )

            return




        if data == "users":

            await query.edit_message_text(
f"""
👥 USERS

Total:
{get_users_count()}
""",
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

            status = toggle_signal()


            await query.edit_message_text(
f"""
🚀 Signal Control


Signal Status:
{status}
""",
                reply_markup=admin_keyboard()
            )

            return
                    if data == "ai_settings":

            await query.edit_message_text(
f"""
🧠 AI SETTINGS


Mode:
{get_setting("ai_mode")}


Score:
{get_setting("minimum_score")}
""",
                reply_markup=admin_keyboard()
            )

            return





        if data == "channel_lock":

            current = get_setting(
                "channel_lock"
            )


            new_status = "OFF"


            if current == "OFF":

                new_status = "ON"


            set_setting(
                "channel_lock",
                new_status
            )


            await query.edit_message_text(
f"""
🔒 Channel Lock


Status:
{new_status}
""",
                reply_markup=admin_keyboard()
            )

            return





    if data == "signal":

        if get_setting("signal_status") == "OFF":

            await query.message.reply_text(
                "⛔ Signal is disabled"
            )

            return


        await query.message.reply_text(
            "🔍 Analyzing XAUUSD..."
        )


        await send_signal(
            query
        )

        return






    if data == "performance":

        await query.edit_message_text(
            create_report(),
            reply_markup=user_keyboard()
        )

        return






    await query.edit_message_text(
        "⚙️ این بخش آماده‌سازی می‌شود",
        reply_markup=admin_keyboard()
    )





# ================= TEXT =================


async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    update_activity(
        update.effective_user.id
    )


    text = update.message.text.upper()


    if text.startswith("SIGNAL"):

        if get_setting("signal_status") == "OFF":

            await update.message.reply_text(
                "⛔ Signal Disabled"
            )

            return


        await send_signal(
            update
        )





# ================= RUN =================


create_users_table()

create_database()

init_settings()



app = Application.builder().token(
    TOKEN
).build()



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
