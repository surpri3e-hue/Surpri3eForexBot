from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import os

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Surpri3e Forex Bot Online\n\nCommands:\nSignal M1\nSignal M5"
    )

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper()

    if text == "SIGNAL M1":
        await update.message.reply_text(
            "📊 XAUUSD M1\n\nAnalysis started...\nWaiting for ICT setup."
        )

    elif text == "SIGNAL M5":
        await update.message.reply_text(
            "📊 XAUUSD M5\n\nAnalysis started...\nWaiting for ICT setup."
        )

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, signal))

app.run_polling()
