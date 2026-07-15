# ============================================================
# 📁 signals.py
# 📌 وظیفه: دریافت سیگنال از سبک‌های ICT یا SMC
# 📅 تاریخ: 2026-07-15
# 👤 توسعه‌دهنده: Surpri3e
# ============================================================

from ict_logic import analyze_ict
from smc_logic import analyze_smc


def create_signal(df, style='ICT'):
    """
    ✅ دریافت سیگنال بر اساس سبک انتخابی (ICT یا SMC)

    پارامترها:
        df (DataFrame): دیتای کندلی قیمت طلا
        style (str): سبک مورد نظر ('ICT' یا 'SMC')

    خروجی:
        signal (dict): شامل direction, entry, sl, tp
        analysis (dict): شامل reasons و style
        در صورت خطا: (None, None)
    """

    # ===== بررسی دیتا =====
    # حداقل ۳۰ کندل برای تحلیل نیاز داریم
    if df is None or len(df) < 30:
        return None, None

    # ===== انتخاب سبک =====
    if style == 'ICT':
        signal, analysis = analyze_ict(df)
    elif style == 'SMC':
        signal, analysis = analyze_smc(df)
    else:
        # اگر سبک نامعتبر بود
        return None, None

    # ===== اگر سیگنال پیدا نشد =====
    if signal is None:
        return None, None

    # ===== حذف امتیاز (اگه باشه) =====
    # چون کاربر فقط دلایل رو میبینه، نیازی به امتیاز نیست
    if 'score' in signal:
        del signal['score']
    if 'score' in analysis:
        del analysis['score']

    # ===== برگرداندن سیگنال نهایی =====
    return signal, analysis
