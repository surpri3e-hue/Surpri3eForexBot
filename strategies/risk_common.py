# ============================================================
# 📁 strategies/risk_common.py
# 📌 توابع مشترک محاسبه‌ی ریسک بین همه‌ی استراتژی‌ها.
#
# ⚠️ تغییر مهم (۲۰۲۶-۰۷-۲۱): قبلاً هر استراتژی فاصله‌ی SL/TP رو از روی
# ATR (نوسان واقعی کندل‌ها) محاسبه می‌کرد، و برای مود اسکلپ یک محدودیت
# زمانی جداگانه هم داشت. طبق تصمیم پروژه، این منطق کاملاً با یک فاصله‌ی
# پیپ ثابت و سراسری جایگزین شده که فقط از پنل ادمین قابل تنظیمه - همه‌ی
# کاربران و همه‌ی نمادها همیشه از همین یک عدد استفاده می‌کنن.
# ============================================================


def get_stop_distance(symbol='XAU/USD'):
    """
    فاصله‌ی استاپ (Entry تا SL) رو بر حسب واحد قیمتی (دلار) برمی‌گردونه.

    محاسبه: (فاصله‌ی پیپ سراسری از پنل ادمین) × (ارزش هر پیپ برای این نماد)

    مثال: اگه ادمین «stop_distance_pips=30» و «pip_value_xau=0.1» تنظیم
    کرده باشه، برای طلا خروجی = 30 × 0.1 = 3.0 دلار فاصله.

    خروجی: float - فاصله‌ی قیمتی بین Entry و SL
    """
    from database import get_setting

    stop_pips = float(get_setting('stop_distance_pips') or '30')

    symbol_normalized = (symbol or 'XAU/USD').upper()
    if 'BTC' in symbol_normalized:
        pip_value = float(get_setting('pip_value_btc') or '1')
    else:
        # ===== پیش‌فرض طلا/سایر نمادها =====
        pip_value = float(get_setting('pip_value_xau') or '0.1')

    return stop_pips * pip_value
