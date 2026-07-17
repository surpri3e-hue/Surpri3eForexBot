# ============================================================
# 📁 auto_tracker.py
# 📌 وظیفه: بررسی خودکار معاملات باز (OPEN) بر اساس قیمت زنده،
#          و ثبت خودکار نتیجه (TP/SL) + اطلاع‌رسانی به کاربر.
# 📅 ساخته‌شده: 2026-07-17
#
# این به‌عنوان یه background task با asyncio اجرا می‌شه (نه یه
# Thread جدا)، چون داخل همون event loop که python-telegram-bot
# استفاده می‌کنه اجرا میشه و نیازی به قفل/هماهنگی جداگانه نداره.
# ============================================================

import asyncio
import logging

from database import get_open_trades, update_result
from market import get_current_price

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60  # هر ۶۰ ثانیه یک‌بار قیمت رو چک می‌کنه


async def check_open_trades_once(bot):
    """
    یک بار همه‌ی معاملات باز رو با قیمت لحظه‌ای مقایسه می‌کنه.
    اگه TP یا SL خورده باشه، نتیجه رو ثبت می‌کنه و به کاربر پیام می‌ده.
    """
    trades = get_open_trades()
    if not trades:
        return

    price = get_current_price()
    if price is None:
        logger.warning("قیمت لحظه‌ای در دسترس نیست - چک خودکار TP/SL این دور رد شد")
        return

    for trade in trades:
        trade_id = trade['id']
        user_id = trade['user_id']
        direction = trade['direction']
        sl = trade['sl']
        tp = trade['tp']

        hit_result = None

        if direction == 'BUY':
            if price >= tp:
                hit_result = 'TP'
            elif price <= sl:
                hit_result = 'SL'
        elif direction == 'SELL':
            if price <= tp:
                hit_result = 'TP'
            elif price >= sl:
                hit_result = 'SL'

        if hit_result:
            update_result(trade_id, hit_result)
            emoji = "✅" if hit_result == "TP" else "❌"
            try:
                if user_id and user_id != 0:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"{emoji} **معامله‌ی شماره {trade_id} به‌صورت خودکار {hit_result} شد.**\n\n💰 قیمت لحظه‌ای: {price:.2f}",
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.warning(f"اطلاع‌رسانی خودکار TP/SL به کاربر {user_id} ناموفق بود: {e}")


async def auto_tracker_loop(application):
    """
    حلقه‌ی بی‌نهایت که هر CHECK_INTERVAL_SECONDS ثانیه معاملات باز رو چک می‌کنه.
    این به‌عنوان یه asyncio task جدا از application.run_polling() اجرا می‌شه.
    """
    logger.info("🔄 چک خودکار TP/SL شروع شد.")
    while True:
        try:
            await check_open_trades_once(application.bot)
        except Exception as e:
            logger.exception(f"خطا در چک خودکار TP/SL: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
