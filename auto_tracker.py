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
from concurrent.futures import ThreadPoolExecutor

from database import get_open_trades, update_result
from market import get_current_price

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60  # هر ۶۰ ثانیه یک‌بار قیمت رو چک می‌کنه

# ============================================================
# ⚠️ رفع باگ تأخیر در ارسال TP/SL خودکار: قبلاً get_current_price با
# asyncio.to_thread اجرا می‌شد که از یک ThreadPoolExecutor مشترک و
# پیش‌فرض (سراسری، با ظرفیت محدود - معمولاً فقط ۵ ترد روی سرورهای کم‌هسته
# مثل Railway) استفاده می‌کنه. وقتی چند کاربر هم‌زمان منتظر سیگنال بودن
# (که هرکدوم مکرراً get_gold_candles رو صدا می‌زنه و یک ترد اشغال
# می‌کنه)، این pool مشترک پر می‌شد و auto_tracker مجبور می‌شد پشت صف
# بمونه - نتیجه: پیام TP/SL با تأخیر چند دقیقه‌ای (به‌جای ۶۰ ثانیه) می‌رسید.
#
# ✅ راه‌حل: یک ThreadPoolExecutor اختصاصی فقط برای auto_tracker، که هیچ‌وقت
# با ترافیک سیگنال‌گیری رقابت نمی‌کنه - پس چک TP/SL همیشه دقیقاً هر ۶۰
# ثانیه اجرا می‌شه، صرف‌نظر از این‌که چند نفر هم‌زمان سیگنال می‌گیرن.
# ============================================================
_tracker_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="auto_tracker")


async def _run_in_tracker_thread(func, *args):
    """اجرای یک تابع blocking در Executor اختصاصی auto_tracker (نه pool مشترک asyncio)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_tracker_executor, func, *args)


async def check_open_trades_once(bot):
    """
    یک بار همه‌ی معاملات باز رو با قیمت لحظه‌ای مقایسه می‌کنه.
    اگه TP یا SL خورده باشه، نتیجه رو ثبت می‌کنه و به کاربر پیام می‌ده.

    ⚠️ هر معامله بر اساس نماد خودش (symbol) چک می‌شه - نه یک قیمت واحد
    برای همه. قبلاً این تابع فقط قیمت طلا رو می‌گرفت و همون رو برای
    معاملات بیت‌کوین هم استفاده می‌کرد که کاملاً اشتباه بود.

    ⚠️ رفع باگ کندی ربات: get_current_price از requests (synchronous/blocking)
    استفاده می‌کنه. چون این تابع هر ۶۰ ثانیه در همون event loop اصلی که
    به همه‌ی کاربرا سرویس می‌ده اجرا می‌شد، هر بار که این API فراخوانی
    می‌شد، کل ربات برای همه‌ی کاربرا (تا وقتی جواب API برسه) فریز می‌شد.
    حالا با asyncio.to_thread در یک ترد جدا اجرا می‌شه تا event loop اصلی
    همیشه آزاد بمونه.
    """
    trades = get_open_trades()
    if not trades:
        return

    # ===== گروه‌بندی معاملات بر اساس نماد، تا برای هر نماد فقط یک بار قیمت گرفته بشه =====
    trades_by_symbol = {}
    for trade in trades:
        symbol = trade.get('symbol', 'XAU/USD')
        trades_by_symbol.setdefault(symbol, []).append(trade)

    for symbol, symbol_trades in trades_by_symbol.items():
        price = await _run_in_tracker_thread(get_current_price, symbol)
        if price is None:
            logger.warning(f"قیمت لحظه‌ای برای {symbol} در دسترس نیست - چک این نماد در این دور رد شد")
            continue

        for trade in symbol_trades:
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
                            text=f"{emoji} **معامله‌ی شماره {trade_id} ({symbol}) به‌صورت خودکار {hit_result} شد.**\n\n💰 قیمت لحظه‌ای: {price:.2f}",
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
