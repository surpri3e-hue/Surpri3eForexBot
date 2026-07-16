import numpy as np

# ============================================================
# 🚀 تنظیمات آپدیت شده و خفن (Surpri3e Strategy 2.0)
# ============================================================
DEPTH_ENGINE = 5        # حساسیت بهینه‌شده برای شکار سریع‌تر چرخش‌ها
DEVIATION_ENGINE = 2.5  # کاهش سخت‌گیری نوسانات برای پیدا کردن سیگنال‌های بیشتر
MAX_PIVOT_AGE_BARS = 30 # بررسی کندل‌ها تا 30 کندل قبل (طبق درخواست شما)


def _find_raw_pivots(high, low, depth):
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
    if df is None or len(df) < 30:
        return None, None

    is_real = df.attrs.get('is_real_data', True)

    zz = get_zigzag_signal(df)
    if not zz:
        return None, None

    # بررسی تا حداکثر 30 کندل قبل
    if zz['bars_ago'] > MAX_PIVOT_AGE_BARS:
        return None, None

    direction = zz['direction']
    current = float(df['Close'].iloc[-1])

    from database import get_setting
    rr_ratio = float(get_setting('rr_ratio') or '2')

    # 🔥 مدیریت ریسک حرفه‌ای: قرار دادن استاپ لاس دقیقاً روی نقطه‌ی چرخش (Pivot)
    if direction == "BUY":
        entry = round(current, 2)
        sl = round(zz['pivot_price'] - 0.5, 2) # نیم دلار پایین‌تر از دره برای اطمینان
        risk = entry - sl
        
        # جلوگیری از ریسک‌های نامنطقی
        if risk < 2.0: risk = 2.0
        if risk > 15.0: risk = 15.0
        
        tp = round(entry + (risk * rr_ratio), 2)
    else:
        entry = round(current, 2)
        sl = round(zz['pivot_price'] + 0.5, 2) # نیم دلار بالاتر از قله
        risk = sl - entry
        
        if risk < 2.0: risk = 2.0
        if risk > 15.0: risk = 15.0
        
        tp = round(entry - (risk * rr_ratio), 2)

    reasons = [
        f"نقطه‌ی چرخش ZigZag در سطح {zz['pivot_price']:.2f} ({zz['bars_ago']} کندل قبل)"
    ]

    if not is_real:
        reasons = ["⚠️ هشدار: این تحلیل روی داده‌ی تستی/شبیه‌سازی‌شده انجام شده، نه قیمت واقعی بازار"] + reasons

    signal = {
        'direction': direction,
        'entry': entry,
        'sl': sl,
        'tp': tp,
        'strength': 'STRONG', # سیگنال‌ها با این آپدیت قدرتمندتر هستند
    }

    analysis = {
        'reasons': reasons,
        'style': 'Surpri3e Strategy',
        'score': None,
        'strength': 'STRONG',
    }

    return signal, analysis
