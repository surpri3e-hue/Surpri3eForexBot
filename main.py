from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

import os

from market import get_gold_candles
from ict import ict_analysis
from signals import create_signal
from database import save_trade
from report import create_report
from chart import create_chart


TOKEN = os.getenv("BOT_TOKEN")



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""
🤖 Surpri3e AI Forex Bot Online

Commands:

Signal M1
Signal M5
Signal M15
Signal M30
Signal H1
Signal H4

Status
"""
    )




async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):


    text = update.message.text.upper()



    # گزارش

    if text == "STATUS":

        await update.message.reply_text(
            create_report()
        )

        return




    if not text.startswith("SIGNAL"):

        return




    tf = text.replace(
        "SIGNAL ",
        ""
    )



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
            "❌ Invalid timeframe"
        )

        return





    loading = await update.message.reply_text(

f"""
🤖 Surpri3e AI Scanner

XAUUSD {tf}

Analyzing...

🔍 Checking ICT Model

Liquidity
⏳

FVG
⏳

Structure
⏳

Entry
⏳
"""

    )




    df = get_gold_candles(
        intervals[tf]
    )



    if df is None:


        await loading.edit_text(
"""
❌ Data Error

Cannot receive XAUUSD data.
"""
        )

        return





    analysis = ict_analysis(df)



    signal = create_signal(
        df,
        analysis
    )






    if signal:



        save_trade(signal)



        chart_file = create_chart(
            df,
            signal,
            tf
        )



        result = f"""
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

Score:
{signal['score']}/100

Reason:

{', '.join(signal['reason'])}
"""



        await loading.edit_text(
            result
        )



        with open(chart_file,"rb") as photo:


            await update.message.reply_photo(

                photo=photo,

                caption="📊 ICT Chart"

            )




    else:



        await loading.edit_text(

f"""
❌ No Setup

XAUUSD {tf}

ICT conditions are not ready.

Wait for next signal.
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
