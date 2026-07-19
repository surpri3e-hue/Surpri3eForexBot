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


def create_signal(df, style='surpri3e', rr_override=None):
    """
    دریافت سیگنال بر اساس استراتژی انتخابی.

    پارامترها:
        df (DataFrame): دیتای کندلی قیمت طلا
        style (str): شناسه‌ی استراتژی (مثلاً 'surpri3e')
        rr_override (float|None): RR اختصاصی کاربر - اگه داده بشه، به‌جای
            RR سراسری تنظیمات ربات برای محاسبه‌ی SL/TP استفاده می‌شه.

    خروجی:
        signal (dict): شامل direction, entry, sl, tp, strength
        analysis (dict): شامل reasons, style, score, strength
        در صورت نبود ستاپ معتبر یا نبود استراتژی: (None, None)
    """
    if df is None or len(df) < 30:
        return None, None

    # سازگاری با مقادیر قدیمی که ممکنه هنوز تو دیتابیس کاربرها باشه
    style_normalized = style.lower() if style else 'surpri3e'
    if style_normalized in ('surpri3e', 'ict', 'smc'):
        style_normalized = 'surpri3e'

    return run_strategy(style_normalized, df, rr_override=rr_override)
