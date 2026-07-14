from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import os
import requests

TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("TWELVE_API_KEY")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Surpri3e Forex Bot Online\n\nCommands:\nSignal M1\nSignal M5"
    )


def get_gold_data(interval):
    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": "XAU/USD",
        "interval": interval,
        "outputsize": 5,
        "apikey": API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    return data


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper()

    if text == "SIGNAL M1":
        interval = "1min"

    elif text == "SIGNAL M5":
        interval = "5min"

    else:
        return

    data = get_gold_data(interval)

    if "values" in data:
        last = data["values"][0]

        msg = f"""
📊 XAUUSD {interval}

Open: {last['open']}
High: {last['high']}
Low: {last['low']}
Close: {last['close']}

✅ Data received
Waiting for ICT analysis...
"""
    else:
        msg = f"❌ Data error:\n{data}"

    await update.message.reply_text(msg)


app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, signal))

app.run_polling()
