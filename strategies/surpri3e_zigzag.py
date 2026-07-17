# ============================================================
# 📁 strategies/surpri3e_zigzag.py
# 📌 Surpri3e Strategy - استراتژی مستقل بر پایه‌ی نقاط چرخش ZigZag
#    (بر اساس منطق Pine Script buysellsignal-yashgode9)
# 📅 نسخه‌ی plugin-محور: 2026-07-17
#
# این فایل از معماری استاندارد استراتژی‌های ربات پیروی می‌کنه:
#   - STRATEGY_INFO: مشخصات نمایشی + پارامترهای قابل‌تنظیم از پنل ادمین
#   - analyze(df): تابع اصلی تحلیل، امضای یکسان با همه‌ی استراتژی‌ها
#
# پارامترهای این استراتژی از دیتابیس (strategy_settings) خونده می‌شن؛
# اگه هنوز از پنل ادمین تغییری داده نشده باشن، مقادیر DEFAULT همینجا
# استفاده می‌شه.
# ============================================================

import numpy as np

STRATEGY_ID = "surpri3e"

STRATEGY_INFO = {
    "id": STRATEGY_ID,
    "display_name": "🌀 Surpri3e Strategy",
    "description": "بر پایه‌ی نقاط چرخش ZigZag (Pine Script buysellsignal-yashgode9)",
    # پارامترهای قابل‌تنظیم از پنل ادمین: نام، مقدار پیش‌فرض، نوع، بازه‌ی مجاز
    "params": {
        "depth": {
            "label": "عمق تشخیص Pivot (Depth)",
            "default": 7,
            "type": "int",
            "min": 3,
            "max": 20,
            "help": "عدد بزرگتر = فیلتر نویز قوی‌تر، سیگنال کمتر ولی معتبرتر",
        },
        "deviation": {
            "label": "حداقل نوسان قیمتی (Deviation)",
            "default": 4.0,
            "type": "float",
            "min": 0.5,
            "max": 20.0,
            "help": "حداقل فاصله‌ی قیمتی بین دو نقطه‌ی چرخش هم‌جهت متوالی",
        },
        "max_age": {
            "label": "حداکثر قدمت نقطه‌ی چرخش (کندل)",
            "default": 15,
            "type": "int",
            "min": 3,
            "max": 50,
            "help": "نقطه‌ی چرخشی که قدیمی‌تر از این باشه، دیگه معتبر نیست",
        },
    },
}

# حداقل و حداکثر منطقی برای فاصله‌ی SL از entry (به دلار) - ثابت، نه از پنل ادمین
MIN_RISK = 2.0
MAX_RISK = 15.0
SL_BUFFER = 0.5  # فاصله‌ی اطمینان اضافه از خودِ نقطه‌ی pivot


def _get_param(strategy_id, param_name):
    """پارامتر رو از دیتابیس می‌خونه؛ اگه ذخیره نشده بود، مقدار پیش‌فرض این فایل."""
    from database import get_strategy_setting
    param_def = STRATEGY_INFO["params"][param_name]
    raw = get_strategy_setting(strategy_id, param_name, default=None)
    if raw is None:
        return param_def["default"]
    if param_def["type"] == "int":
        return int(raw)
    return float(raw)


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


def get_zigzag_signal(df, depth=None, deviation=None):
    """
    تحلیل ZigZag روی دیتافریم کندلی. خروجی dict یا None:
        {'direction': 'BUY'|'SELL', 'pivot_price': float, 'bars_ago': int}
    """
    if depth is None:
        depth = _get_param(STRATEGY_ID, "depth")
    if deviation is None:
        deviation = _get_param(STRATEGY_ID, "deviation")

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


def analyze(df):
    """
    تابع اصلی تحلیل - امضای استاندارد همه‌ی استراتژی‌های plugin.
    خروجی: (signal: dict, analysis: dict) یا (None, None)
    """
    if df is None or len(df) < 30:
        return None, None

    is_real = df.attrs.get('is_real_data', True)

    depth = _get_param(STRATEGY_ID, "depth")
    deviation = _get_param(STRATEGY_ID, "deviation")
    max_age = _get_param(STRATEGY_ID, "max_age")

    zz = get_zigzag_signal(df, depth=depth, deviation=deviation)
    if not zz:
        return None, None

    if zz['bars_ago'] > max_age:
        return None, None

    direction = zz['direction']
    current = float(df['Close'].iloc[-1])

    from database import get_setting
    rr_ratio = float(get_setting('rr_ratio') or '2')

    entry = round(current, 2)

    if direction == "BUY":
        raw_risk = entry - (zz['pivot_price'] - SL_BUFFER)
    else:
        raw_risk = (zz['pivot_price'] + SL_BUFFER) - entry

    risk = max(MIN_RISK, min(MAX_RISK, raw_risk))

    # SL/TP نهایی همیشه از entry + risk نهایی (بعد از clamp) ساخته می‌شه
    if direction == "BUY":
        sl = round(entry - risk, 2)
        tp = round(entry + (risk * rr_ratio), 2)
    else:
        sl = round(entry + risk, 2)
        tp = round(entry - (risk * rr_ratio), 2)

    # قدرت سیگنال: نسبت به depth سنجیده می‌شه (چون کمترین bars_ago ممکن = depth است)
    freshness_threshold = depth + 3
    strength = 'NORMAL' if zz['bars_ago'] <= freshness_threshold else 'WEAK'

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
        'style': STRATEGY_INFO["display_name"],
        'score': None,
        'strength': strength,
    }

    return signal, analysis
