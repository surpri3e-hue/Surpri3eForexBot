# ============================================================
# 📁 signals.py
# 📌 وظیفه: دریافت سیگنال از استراتژی انتخاب‌شده، از طریق registry
# 📅 بازنویسی: 2026-07-17 - معماری plugin-محور
#
# دیگه به‌طور مستقیم به فایل استراتژی خاصی (مثل zigzag_logic) وابسته
# نیست؛ از strategy_registry می‌خواد که استراتژی رو با شناسه‌اش پیدا
# و اجرا کنه. افزودن استراتژی جدید فقط نیاز به ساخت فایل در پوشه‌ی
# strategies/ داره، بدون تغییر این فایل.
# ============================================================

from strategy_registry import run_strategy


def create_signal(df, style='equal_liquidity', rr_override=None, mode='standard', symbol='XAU/USD', timeframe='5min'):
    """
    دریافت سیگنال بر اساس استراتژی انتخابی.

    پارامترها:
        df (DataFrame): دیتای کندلی قیمت طلا
        style (str): شناسه‌ی استراتژی (مثلاً 'equal_liquidity')
        rr_override (float|None): RR اختصاصی کاربر - اگه داده بشه، به‌جای
            RR سراسری تنظیمات ربات برای محاسبه‌ی SL/TP استفاده می‌شه.
        mode (str): 'standard' یا 'fast_scalp' - در مود اسکلپ فاصله‌ی
            SL/TP به چند دقیقه محدود می‌شه.
        symbol, timeframe: برای استراتژی‌هایی که نیاز به دیتای تایم‌فریم
            دیگری دارن (مثلاً تایید روند تایم‌فریم بالاتر).

    خروجی:
        signal (dict): شامل direction, entry, sl, tp, strength
        analysis (dict): شامل reasons, style, score, strength
        در صورت نبود ستاپ معتبر یا نبود استراتژی: (None, None)
    """
    if df is None or len(df) < 30:
        return None, None

    # ===== سازگاری با مقادیر قدیمی که ممکنه هنوز تو دیتابیس کاربرها باشه =====
    # 'surpri3e' و 'liquidity_sweep' در بک‌تست ضررده بودن و حذف شدن؛
    # کاربرهایی که این مقادیر رو قبلاً انتخاب کرده بودن، خودکار به
    # استراتژی جدید equal_liquidity هدایت می‌شن تا بی‌سیگنال نمونن.
    style_normalized = style.lower() if style else 'equal_liquidity'
    if style_normalized in ('surpri3e', 'liquidity_sweep', 'ict', 'smc'):
        style_normalized = 'equal_liquidity'

    return run_strategy(style_normalized, df, rr_override=rr_override, mode=mode, symbol=symbol, timeframe=timeframe)
