# signals.py
# ================================================================
# این فایل وظیفه دریافت سیگنال از استراتژی Surpri3e را دارد
# استراتژی Surpri3e = Zigzag پیشرفته + اعتبارسنجی کامل
# ================================================================

from zigzag_logic import get_zigzag_signal

# ===== اگر بعداً خواستی ICT یا SMC رو برگردونی، خطوط زیر رو از حالت کامنت خارج کن =====
# from ict_logic import analyze_ict
# from smc_logic import analyze_smc


def create_signal(df, style='ZIGZAG'):
    """
    دریافت سیگنال از استراتژی Surpri3e (زیگزاگ)
    
    پارامترها:
    ----------
    df : DataFrame
        دیتای کندل‌ها (شامل Open, High, Low, Close, Volume)
    style : str
        فقط 'ZIGZAG' پشتیبانی می‌شود
    
    خروجی:
    -------
    signal : dict
        شامل direction, entry, sl, tp
    analysis : dict
        شامل reasons, style
    """
    
    # ===== بررسی دیتا =====
    if df is None or len(df) < 30:
        return None, None
    
    # ===== فقط سبک زیگزاگ =====
    if style != 'ZIGZAG':
        # اگر سبک دیگری انتخاب شده بود، به زیگزاگ تغییر بده
        style = 'ZIGZAG'
    
    # ===== دریافت سیگنال از زیگزاگ =====
    signal, analysis = get_zigzag_signal(df)
    
    # ===== اگر سیگنال وجود نداشت =====
    if signal is None:
        return None, None
    
    # ===== حذف امتیاز (اگه باشه) =====
    if 'score' in signal:
        del signal['score']
    if 'score' in analysis:
        del analysis['score']
    
    # ===== اطمینان از وجود استایل =====
    analysis['style'] = 'Surpri3e Strategy'
    
    return signal, analysis


# ================================================================
# ===== در صورت نیاز به برگرداندن ICT یا SMC، این بخش رو فعال کن =====
# ================================================================

# def create_signal_all_styles(df, style='ZIGZAG'):
#     """
#     دریافت سیگنال از هر سه سبک (ICT, SMC, ZIGZAG)
#     """
#     if df is None or len(df) < 30:
#         return None, None
#     
#     if style == 'ICT':
#         signal, analysis = analyze_ict(df)
#     elif style == 'SMC':
#         signal, analysis = analyze_smc(df)
#     elif style == 'ZIGZAG':
#         signal, analysis = get_zigzag_signal(df)
#     else:
#         return None, None
#     
#     if signal is None:
#         return None, None
#     
#     if 'score' in signal:
#         del signal['score']
#     if 'score' in analysis:
#         del analysis['score']
#     
#     return signal, analysis
