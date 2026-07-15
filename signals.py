# ============================================================
# 📁 signals.py
# 📌 وظیفه: دریافت سیگنال از سبک‌های ICT یا SMC
# 📅 بازنویسی: 2026-07-15
# ============================================================

from ict_logic import analyze_ict
from smc_logic import analyze_smc


def create_signal(df, style='ICT'):
    """
    دریافت سیگنال بر اساس سبک انتخابی (ICT یا SMC)

    پارامترها:
        df (DataFrame): دیتای کندلی قیمت طلا
        style (str): سبک مورد نظر ('ICT' یا 'SMC')

    خروجی:
        signal (dict): شامل direction, entry, sl, tp, strength
        analysis (dict): شامل reasons, style, score, strength
        در صورت نبود ستاپ معتبر: (None, None)
    """
    if df is None or len(df) < 30:
        return None, None

    if style == 'ICT':
        return analyze_ict(df)
    elif style == 'SMC':
        return analyze_smc(df)
    else:
        return None, None
