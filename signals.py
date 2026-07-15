# signals.py
import numpy as np

# ===== اینجا توابع تحلیل رو مستقیم import می‌کنیم =====
from ict_logic import analyze_ict
from smc_logic import analyze_smc


def create_signal(df, style='ICT'):
    """
    دریافت سیگنال بر اساس سبک انتخابی
    """
    # ===== بررسی دیتا =====
    if df is None or len(df) < 20:
        return None, None

    # ===== انتخاب سبک =====
    if style == 'ICT':
        signal, analysis = analyze_ict(df)
    elif style == 'SMC':
        signal, analysis = analyze_smc(df)
    else:
        return None, None

    # ===== اگر سیگنال وجود نداشت =====
    if signal is None:
        return None, None

    # ===== حذف امتیاز =====
    if 'score' in signal:
        del signal['score']
    if 'score' in analysis:
        del analysis['score']

    return signal, analysis
