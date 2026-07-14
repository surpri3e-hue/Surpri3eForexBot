from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

import os

from market import get_gold_candles
from ict import ict_analysis
from signals import create_signal
from database import save_trade
from report import create_report


TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Surpri3e Forex Bot Online\n\n"
        "Commands:\n"
        "Signal M1\n"
        "Signal M5\n"
        "Status"
    )



async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.upper()


    if text == "STATUS":

        await update.message.reply_text(
            create_report()
        )

        return



    if text.startswith("SIGNAL"):


        tf = text.replace("SIGNAL ", "")


        intervals = {
            "M1": "1min",
            "M5": "5min",
            "M15": "15min",
            "M30": "30min",
            "H1": "1h",
            "H4": "4h",
            "D1": "1day",
            "W1": "1week",
            "MN1": "1month"
        }


        if tf not in intervals:

            await update.message.reply_text(
                "❌ Invalid timeframe"
            )
            return



        await update.message.reply_text(
            f"🔍 Scanning XAUUSD {tf}..."
        )


        df = get_gold_candles(
            intervals[tf]
        )


        if df is None:

            await update.message.reply_text(
                "❌ Market data error"
            )
            return



        analysis = ict_analysis(df)


        signal = create_signal(
            df,
            analysis
        )


        if signal:


            save_trade(signal)


            msg = f"""
🚨 ICT SIGNAL FOUND

XAUUSD {tf}

Direction:
{signal['direction']}

Entry:
{signal['entry']}

SL:
{signal['sl']}

TP:
{signal['tp']}

RR:
{signal['rr']}

Reason:
{', '.join(signal['reason'])}
"""

        else:

            msg = """
❌ No High Quality Setup

Waiting for better ICT conditions.
"""


        await update.message.reply_text(msg)



app = Application.builder().token(TOKEN).build()


app.add_handler(CommandHandler("start", start))

app.add_handler(
    MessageHandler(
        filters.TEXT,
        handler
    )
)


app.run_polling()
