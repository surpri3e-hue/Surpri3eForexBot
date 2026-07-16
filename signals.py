# ============================================================
# 📁 signals.py
# 📌 وظیفه: دریافت سیگنال از Surpri3e Strategy
# 📅 بازنویسی: 2026-07-16 - حذف وابستگی به ict_logic/smc_logic
#                            (این دو دیگر از دکمه‌های ربات صدا زده
#                            نمی‌شوند و وابستگی‌شان به کتابخونه‌ی ta
#                            باعث کرش روی Railway می‌شد)
# ============================================================

from zigzag_logic import analyze_surpri3e_strategy


def create_signal(df, style='SURPRI3E'):
    """
    دریافت سیگنال بر اساس Surpri3e Strategy (مبتنی بر ZigZag).

    پارامترها:
        df (DataFrame): دیتای کندلی قیمت طلا
        style (str): در حال حاضر فقط 'SURPRI3E' پشتیبانی می‌شود

    خروجی:
        signal (dict): شامل direction, entry, sl, tp, strength
        analysis (dict): شامل reasons, style, score, strength
        در صورت نبود ستاپ معتبر: (None, None)
    """
    if df is None or len(df) < 30:
        return None, None

    if style == 'SURPRI3E':
        return analyze_surpri3e_strategy(df)
    else:
        return None, None
