import os

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from market import get_gold_candles
from ict import ict_analysis
from signals import create_signal
from database import save_trade
from report import create_report


TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Surpri3e AI Bot Online"
    )



async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.upper()


    if text == "STATUS":

        await update.message.reply_text(
            create_report()
        )

        return



    if not text.startswith("SIGNAL"):

        return



    tf = text.replace("SIGNAL ","")


    intervals = {
        "M1":"1min",
        "M5":"5min",
        "M15":"15min",
        "M30":"30min",
        "H1":"1h",
        "H4":"4h"
    }


    if tf not in intervals:

        await update.message.reply_text(
            "❌ Wrong timeframe"
        )

        return



    await update.message.reply_text(
        "🔍 Analyzing XAUUSD..."
    )



    df = get_gold_candles(
        intervals[tf]
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




app = Application.builder().token(TOKEN).build()


app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


app.add_handler(
    MessageHandler(
        filters.TEXT,
        handler
    )
)


app.run_polling()
