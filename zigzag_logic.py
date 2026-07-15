# ============================================================
# 📁 zigzag_logic.py
# 📌 وظیفه: پیاده‌سازی منطق اندیکاتور ZigZag (بر اساس Pine Script
#          buysellsignal-yashgode9) به‌عنوان لایه‌ی تاییدی اضافه
#          روی امتیازدهی ICT/SMC.
#
# منطق اصلی معادل با:
#   isHigh = ta.pivothigh(high, depth, depth)
#   isLow  = ta.pivotlow(low, depth, depth)
#   + فیلتر deviation برای رد نوسانات کوچک
#
# ⚠️ نکته‌ی مهم: خود این اندیکاتور در Pine Script با repaint=true
# کار می‌کنه، یعنی pivot نمایش داده‌شده در نزدیکی لبه‌ی داده ممکنه
# با آمدن کندل‌های بعدی عوض بشه. به همین دلیل در این پیاده‌سازی
# فقط از pivot های "تثبیت‌شده" (که حداقل depth کندل بعدشون هم
# موجوده) استفاده می‌کنیم؛ pivot لبه‌ی داده نادیده گرفته می‌شه.
# ============================================================

import numpy as np

DEPTH_ENGINE = 8        # تنظیم‌شده برای سازگاری با تعداد کندل واقعی ربات (۵۰ کندل)
                         # مقدار پیش‌فرض اسکریپت اصلی (30) به حداقل ۶۵ کندل نیاز داره
                         # که با تنظیمات فعلی market.py (count=50) هرگز pivot معتبر برنمی‌گردونه
DEVIATION_ENGINE = 5    # حداقل فاصله‌ی قیمتی بین دو pivot متوالی هم‌جهت


def _find_raw_pivots(high, low, depth):
    """
    معادل ta.pivothigh / ta.pivotlow.
    فقط pivot هایی که کاملاً تثبیت شدن (depth کندل قبل و بعدشون موجوده) برمی‌گردونه.
    خروجی: لیست تاپل (index, price, direction) - direction: 1=high, -1=low
    """
    n = len(high)
    pivots = []
    if n < depth * 2 + 1:
        return pivots

    for i in range(depth, n - depth):
        window_high = high[i - depth:i + depth + 1]
        window_low = low[i - depth:i + depth + 1]

        if high[i] == np.max(window_high):
            pivots.append((i, high[i], 1))
        elif low[i] == np.min(window_low):
            pivots.append((i, low[i], -1))

    return pivots


def _apply_zigzag_filter(pivots, deviation):
    """
    معادل بخش اصلی تابع zigzag() در Pine Script:
    فقط جهت‌های متناوب (High -> Low -> High...) رو نگه می‌داره و
    pivot هایی که فاصله‌ی قیمتی‌شون از pivot هم‌جهت قبلی کمتر از
    deviation باشه رو فیلتر می‌کنه.
    """
    if not pivots:
        return []

    filtered = []
    last_dir = 0
    last_price = None

    for idx, price, direction in pivots:
        if last_dir == 0:
            filtered.append((idx, price, direction))
            last_dir = direction
            last_price = price
            continue

        if direction == last_dir:
            # همون جهت قبلی - فقط اگه نوسان کافی داشت جایگزین کن
            if abs(price - last_price) > deviation:
                filtered[-1] = (idx, price, direction)
                last_price = price
            continue

        # جهت عوض شده - چک deviation نسبت به pivot مخالف قبلی
        if abs(price - last_price) > deviation:
            filtered.append((idx, price, direction))
            last_dir = direction
            last_price = price

    return filtered


def get_zigzag_signal(df, depth=DEPTH_ENGINE, deviation=DEVIATION_ENGINE):
    """
    تحلیل ZigZag رو روی دیتافریم کندلی اجرا می‌کنه و آخرین نقطه‌ی
    چرخش تثبیت‌شده رو برمی‌گردونه.

    خروجی: dict یا None
        {
            'direction': 'BUY' یا 'SELL',   # جهت پیشنهادی بر اساس آخرین چرخش
            'pivot_price': float,            # قیمت نقطه‌ی چرخش
            'bars_ago': int,                 # چند کندل قبل شکل گرفته
        }

    منطق تبدیل جهت (مطابق اسکریپت اصلی):
        direction < 0 (یعنی آخرین pivot از نوع LOW بوده) -> "Buy-point"
        direction > 0 (یعنی آخرین pivot از نوع HIGH بوده) -> "Sell-point"
    """
    if df is None or len(df) < depth * 2 + 5:
        return None

    high = df['High'].values
    low = df['Low'].values

    raw_pivots = _find_raw_pivots(high, low, depth)
    if not raw_pivots:
        return None

    zz_pivots = _apply_zigzag_filter(raw_pivots, deviation)
    if not zz_pivots:
        return None

    last_idx, last_price, last_direction = zz_pivots[-1]

    # طبق منطق اسکریپت: pivot از نوع LOW (direction=-1) یعنی نقطه‌ی Buy،
    # pivot از نوع HIGH (direction=1) یعنی نقطه‌ی Sell
    signal_direction = "BUY" if last_direction == -1 else "SELL"

    return {
        'direction': signal_direction,
        'pivot_price': round(float(last_price), 2),
        'bars_ago': len(df) - 1 - last_idx,
    }
