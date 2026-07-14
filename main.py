import os
import asyncio

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from market import get_gold_candles
from ict import ict_analysis
from signals import create_signal
from database import save_trade
from report import create_report
from chart import create_chart
from tracker import check_trades


TOKEN = os.getenv("BOT_TOKEN")



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""
🤖 Surpri3e AI Scanner Online

Commands:

Signal M1
Signal M5
Signal M15
Signal M30
Signal H1
Signal H4

STATUS
"""
    )



async def tracker_loop():

    while True:

        try:
            check_trades()

        except Exception as e:

            print(
                "Tracker Error:",
                e
            )


        await asyncio.sleep(60)





async def signal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.upper()



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



    timeframes = {

        "M1": "1min",
        "M5": "5min",
        "M15": "15min",
        "M30": "30min",
        "H1": "1h",
        "H4": "4h"

    }



    if tf not in timeframes:

        await update.message.reply_text(
            "❌ تایم فریم اشتباه است"
        )

        return



    msg = await update.message.reply_text(
f"""
🤖 Surpri3e AI Scanner

XAUUSD {tf}

🔍 Analyzing ICT...
"""
    )



    df = get_gold_candles(
        timeframes[tf]
    )



    if df is None:

        await msg.edit_text(
"""
❌ Data Error

دریافت دیتا مشکل دارد
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


        await msg.edit_text(
f"""
🚨 ICT SIGNAL

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
        )


        try:

            chart = create_chart(
                df,
                signal,
                tf
            )


            with open(chart,"rb") as photo:

                await update.message.reply_photo(
                    photo=photo,
                    caption="📊 ICT Chart"
                )

        except Exception as e:

            print(
                "Chart Error:",
                e
            )



    else:


        await msg.edit_text(
f"""
❌ No Setup

XAUUSD {tf}

ICT confirmation not enough.
"""
        )






async def main():


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
            signal_handler
        )
    )



    asyncio.create_task(
        tracker_loop()
    )



    print(
        "BOT STARTED"
    )


    app.run_polling()





if __name__ == "__main__":

    asyncio.run(main())
