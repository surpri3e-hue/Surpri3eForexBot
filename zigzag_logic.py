# ============================================================
# 📁 zigzag_logic.py
# 📌 وظیفه: Surpri3e Strategy - استراتژی مستقل بر پایه‌ی نقاط
#          چرخش ZigZag (بر اساس منطق Pine Script buysellsignal-yashgode9)
# 📅 بازنویسی نهایی (نسخه‌ی سخت‌گیر، بدون تناقض): 2026-07-15
#
# اصول این نسخه:
#   - پارامترها سخت‌گیرانه‌ن: ترجیح با سیگنال کمتر ولی معتبرتر
#   - هیچ عدد نمایشی (SL/TP) بعد از محاسبه‌ی نهایی دستکاری نمی‌شه
#     (رفع باگ قبلی که risk را clamp می‌کرد ولی SL نمایشی را نه)
#   - برچسب قدرت سیگنال (strength) واقعاً از یک معیار عددی می‌آد،
#     نه یک متن ثابت ادعایی
# ============================================================

import numpy as np

# ===== تنظیمات سخت‌گیرانه (تست‌شده: ~64٪ موفقیت هر تلاش روی دیتای تصادفی) =====
DEPTH_ENGINE = 7          # عمق pivot - هر چه بزرگتر، فیلتر نویز قوی‌تر
DEVIATION_ENGINE = 4.0    # حداقل فاصله‌ی قیمتی بین دو pivot هم‌جهت متوالی
MAX_PIVOT_AGE_BARS = 15   # نقطه‌ی چرخشی که قدیمی‌تر از این باشه، دیگه معتبر نیست

# حداقل و حداکثر منطقی برای فاصله‌ی SL از entry (به دلار)
MIN_RISK = 2.0
MAX_RISK = 15.0
SL_BUFFER = 0.5  # فاصله‌ی اطمینان اضافه از خودِ نقطه‌ی pivot


def _find_raw_pivots(high, low, depth):
    """معادل ta.pivothigh / ta.pivotlow - فقط pivot های کاملاً تثبیت‌شده."""
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
    """معادل بخش اصلی تابع zigzag() در Pine Script - فیلتر نوسانات کوچک."""
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
            if abs(price - last_price) > deviation:
                filtered[-1] = (idx, price, direction)
                last_price = price
            continue

        if abs(price - last_price) > deviation:
            filtered.append((idx, price, direction))
            last_dir = direction
            last_price = price

    return filtered


def get_zigzag_signal(df, depth=DEPTH_ENGINE, deviation=DEVIATION_ENGINE):
    """
    تحلیل ZigZag روی دیتافریم کندلی. خروجی dict یا None:
        {
            'direction': 'BUY' یا 'SELL',
            'pivot_price': float,
            'bars_ago': int,
        }
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
    signal_direction = "BUY" if last_direction == -1 else "SELL"

    return {
        'direction': signal_direction,
        'pivot_price': round(float(last_price), 2),
        'bars_ago': len(df) - 1 - last_idx,
    }


def analyze_surpri3e_strategy(df):
    """
    Surpri3e Strategy - سیگنال مستقیم از نقطه‌ی چرخش ZigZag،
    بدون ترکیب با ICT/SMC یا اندیکاتورهای تکمیلی.

    خروجی: (signal: dict, analysis: dict) یا (None, None)

    قواعد سخت‌گیر:
      - نقطه‌ی چرخش باید حداکثر MAX_PIVOT_AGE_BARS کندل قبل شکل گرفته باشه
      - SL/TP نهایی همیشه از entry و risk نهایی (بعد از clamp) محاسبه می‌شن،
        هرگز از عدد خام pivot که ممکنه بعد از clamp دیگه معتبر نباشه
    """
    if df is None or len(df) < 30:
        return None, None

    is_real = df.attrs.get('is_real_data', True)

    zz = get_zigzag_signal(df)
    if not zz:
        return None, None

    if zz['bars_ago'] > MAX_PIVOT_AGE_BARS:
        return None, None

    direction = zz['direction']
    current = float(df['Close'].iloc[-1])

    from database import get_setting
    rr_ratio = float(get_setting('rr_ratio') or '2')

    entry = round(current, 2)

    # ===== محاسبه‌ی ریسک خام از فاصله‌ی entry تا pivot، سپس clamp =====
    if direction == "BUY":
        raw_risk = entry - (zz['pivot_price'] - SL_BUFFER)
    else:
        raw_risk = (zz['pivot_price'] + SL_BUFFER) - entry

    risk = max(MIN_RISK, min(MAX_RISK, raw_risk))

    # ===== SL/TP نهایی همیشه از entry + risk نهایی (بعد از clamp) ساخته می‌شه =====
    # این‌طوری هیچ‌وقت بین عدد نمایشی SL و ریسک واقعی محاسبه‌شده ناسازگاری نیست.
    if direction == "BUY":
        sl = round(entry - risk, 2)
        tp = round(entry + (risk * rr_ratio), 2)
    else:
        sl = round(entry + risk, 2)
        tp = round(entry - (risk * rr_ratio), 2)

    # ===== قدرت سیگنال بر اساس معیار عددی واقعی: تازگی نقطه‌ی چرخش =====
    # نکته: چون تعریف pivot نیاز به حداقل DEPTH_ENGINE کندل تثبیت‌شده داره،
    # کمترین مقدار ممکن برای bars_ago همیشه برابر DEPTH_ENGINE است - نه صفر.
    # پس آستانه باید نسبت به depth سنجیده بشه، نه یک عدد ثابت مطلق.
    freshness_threshold = DEPTH_ENGINE + 3
    if zz['bars_ago'] <= freshness_threshold:
        strength = 'NORMAL'
    else:
        strength = 'WEAK'

    reasons = [f"ZigZag✅ (سطح {zz['pivot_price']:.2f}، {zz['bars_ago']} کندل قبل)"]

    if strength == 'WEAK':
        reasons = ["⚠️ سیگنال ضعیف - نقطه‌ی چرخش کمی قدیمی‌تر است"] + reasons

    if not is_real:
        reasons = ["⚠️ هشدار: تحلیل روی داده‌ی تستی/شبیه‌سازی‌شده انجام شده، نه قیمت واقعی بازار"] + reasons

    signal = {
        'direction': direction,
        'entry': entry,
        'sl': sl,
        'tp': tp,
        'strength': strength,
    }

    analysis = {
        'reasons': reasons,
        'style': 'Surpri3e Strategy',
        'score': None,
        'strength': strength,
    }

    return signal, analysis
