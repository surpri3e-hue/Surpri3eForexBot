from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

import os
import asyncio

from market import get_gold_candles
from ict import ict_analysis
from signals import create_signal
from database import save_trade
from report import create_report


TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Surpri3e Forex Bot Online\n\n"
        "Signal M5\n"
        "Signal M15\n"
        "Signal H1\n"
        "Status"
    )


async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.upper()


    if text == "STATUS":

        await update.message.reply_text(create_report())
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
            "❌ تایم فریم اشتباه است"
        )
        return



    loading = await update.message.reply_text(
f"""
🤖 Surpri3e AI Scanner

XAUUSD {tf}

🔍 Starting analysis...

[░░░░░░░░░░] 0%

Searching:
⬜ Liquidity
⬜ CHoCH
⬜ FVG
⬜ Entry

Time:
0/30 min
"""
    )


    signal = None


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



        filled = int(((minute+1)/30)*10)

        bar = "█"*filled + "░"*(10-filled)



        await loading.edit_text(
f"""
🤖 Surpri3e AI Scanner

XAUUSD {tf}

[{bar}]

Progress:
{((minute+1)*100)//30}%

Time:
{minute+1}/30 min


Status:
🔍 Searching ICT setup...

Liquidity: checking
Structure: checking
FVG: checking
Entry: waiting
"""
        )


        await asyncio.sleep(60)




    if signal:


        save_trade(signal)


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


    else:


        result = f"""
❌ No High Quality Setup

XAUUSD {tf}

30 minute scan finished.

No valid entry found.
"""


    await loading.edit_text(result)



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
