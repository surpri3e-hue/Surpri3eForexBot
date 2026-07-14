from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

import os
import asyncio

from market import get_gold_candles
from ict import ict_analysis
from signals import create_signal
from database import save_trade
from report import create_report
from chart import create_chart


TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Surpri3e Forex Bot Online\n\n"
        "Commands:\n"
        "Signal M1\n"
        "Signal M5\n"
        "Signal M15\n"
        "Signal M30\n"
        "Signal H1\n"
        "Signal H4\n"
        "Status"
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



    loading = await update.message.reply_text(
f"""
🤖 Surpri3e AI Scanner

XAUUSD {tf}

Analyzing Market...

🔍 Searching ICT Setup...
"""
    )


    signal = None
    df = None



    for minute in range(30):

        df = get_gold_candles(
            intervals[tf]
        )


        if df is not None:


            analysis = ict_analysis(df)


            signal = create_signal(
                df,
                analysis
            )


            if signal:
                break



        await loading.edit_text(
f"""
🤖 Surpri3e AI Scanner

XAUUSD {tf}

Progress:
{minute+1}/30 minutes

🔍 Scanning ICT Model...

Liquidity:
⏳ Checking

Structure:
⏳ Checking

FVG:
⏳ Checking

Entry:
⏳ Waiting
"""
        )


        await asyncio.sleep(60)




    if signal:


        save_trade(signal)


        chart_file = create_chart(
            df,
            signal,
            tf
        )


        result = f"""
🚨 HIGH QUALITY ICT SIGNAL

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


        await loading.edit_text(result)


        with open(chart_file, "rb") as photo:

            await update.message.reply_photo(
                photo=photo,
                caption="📊 ICT Chart"
            )


    else:


        await loading.edit_text(
f"""
❌ No High Quality Setup

XAUUSD {tf}

30 minute scan completed.
"""
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
