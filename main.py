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

from settings import (
    init_settings,
    get_setting,
    set_setting
)


TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 816822644



# ================= USER PANEL =================


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
                callback_data="user_settings"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)





# ================= ADMIN PANEL =================


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
                "📈 Analytics",
                callback_data="analytics"
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





# ================= AI PANEL =================


def ai_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "🟢 Safe",
                callback_data="ai_safe"
            ),

            InlineKeyboardButton(
                "🟡 Normal",
                callback_data="ai_normal"
            ),

            InlineKeyboardButton(
                "🔴 Aggressive",
                callback_data="ai_aggressive"
            )
        ],

        [
            InlineKeyboardButton(
                "➕ Score",
                callback_data="score_up"
            ),

            InlineKeyboardButton(
                "➖ Score",
                callback_data="score_down"
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="admin_home"
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





# ================= BUTTONS =================


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    data = query.data



    # برگشت کاربر

    if data == "back":

        await query.edit_message_text(
            "🤖 Surpri3e AI Scanner",
            reply_markup=user_keyboard()
        )

        return




    # برگشت ادمین

    if data == "admin_home":

        await query.edit_message_text(
            "🤖 ADMIN PANEL",
            reply_markup=admin_keyboard()
        )

        return





    # تعداد کاربران

    if data == "users":

        if query.from_user.id != ADMIN_ID:
            return


        count = get_users_count()


        await query.edit_message_text(
            f"""
👥 Users

Total:
{count}
""",
            reply_markup=admin_keyboard()
        )

        return






    # داشبورد

    if data == "dashboard":

        await query.edit_message_text(
            f"""
📊 Dashboard


Bot:
🟢 Online


Signal:
{get_setting("signal_status")}


AI Mode:
{get_setting("ai_mode")}


Minimum Score:
{get_setting("minimum_score")}
""",
            reply_markup=admin_keyboard()
        )

        return





    # AI SETTINGS

    if data == "ai_settings":

        await query.edit_message_text(
            f"""
🧠 AI SETTINGS


Mode:
{get_setting("ai_mode")}


Score:
{get_setting("minimum_score")}
""",
            reply_markup=ai_keyboard()
        )

        return





    if data == "ai_safe":

        set_setting(
            "ai_mode",
            "SAFE"
        )


    elif data == "ai_normal":

        set_setting(
            "ai_mode",
            "NORMAL"
        )


    elif data == "ai_aggressive":

        set_setting(
            "ai_mode",
            "AGGRESSIVE"
        )





    elif data == "score_up":

        score = int(
            get_setting("minimum_score")
        )

        score += 5

        set_setting(
            "minimum_score",
            score
        )




    elif data == "score_down":

        score = int(
            get_setting("minimum_score")
        )

        score -= 5

        if score < 0:
            score = 0


        set_setting(
            "minimum_score",
            score
        )




    elif data == "signal":

        if get_setting("signal_status") == "OFF":

            await query.message.reply_text(
                "⛔ Signal system disabled"
            )

            return



        await query.message.reply_text(
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


        return





    else:

        await query.edit_message_text(
            "⚙️ این بخش در حال توسعه است",
            reply_markup=admin_keyboard()
        )

        return





    await query.edit_message_text(
        f"""
🧠 AI SETTINGS


Mode:
{get_setting("ai_mode")}


Score:
{get_setting("minimum_score")}
""",
        reply_markup=ai_keyboard()
    )





# ================= TEXT =================


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
                str(signal)
            )

        else:

            await update.message.reply_text(
                "❌ No Setup"
            )





# ================= RUN =================


create_users_table()

init_settings()


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
