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
        "Commands:\n"
        "Signal M1\n"
        "Signal M5\n"
        "Signal M15\n"
        "Signal H1\n"
        "Status"
    )



async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.upper()


    # گزارش وضعیت
    if text == "STATUS":

        await update.message.reply_text(
            create_report()
        )

        return



    # دریافت سیگنال
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



        # پیام لودینگ
        loading = await update.message.reply_text(
f"""
🤖 Surpri3e AI Scanner

XAUUSD {tf}

Analyzing Market...

[░░░░░░░░░░] 0%

Checking:
⬜ Price Data
⬜ Liquidity
⬜ CHoCH
⬜ FVG
⬜ Entry Model

⏳ Searching for high quality setup...
"""
        )



        # انیمیشن لودینگ
        for i in range(1, 6):

            progress = "█" * i + "░" * (10-i)

            await loading.edit_text(
f"""
🤖 Surpri3e AI Scanner

XAUUSD {tf}

Analyzing Market...

[{progress}] {i*20}%

Checking:
{"✅" if i>=1 else "⬜"} Price Data
{"✅" if i>=2 else "⬜"} Liquidity
{"✅" if i>=3 else "⬜"} CHoCH
{"✅" if i>=4 else "⬜"} FVG
{"✅" if i>=5 else "⬜"} Entry Model

⏳ Searching...
"""
            )

            await asyncio.sleep(2)



        df = get_gold_candles(
            intervals[tf]
        )



        if df is None:

            await loading.edit_text(
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

ICT conditions not completed.

Waiting for next command.
"""



        await loading.edit_text(msg)



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
