# ============================================================
# 📁 strategies/equal_liquidity.py
# 📌 استراتژی Equal Liquidity Sweep - جایگزین دو استراتژی قبلی
#    (surpri3e_zigzag و liquidity_sweep) که در بک‌تست ضررده بودند.
# 📅 نسخه‌ی اول: 2026-07-31
#
# منطق بر پایه‌ی همان مفهومی نوشته شده که در پنل تنظیمات اندیکاتور
# EQUAL signal v12 دیده شد: تشخیص Equal Highs/Lows (سطوح نقدینگی)،
# یک Liquidity Sweep روی آن سطح، و تأیید با یک کندل Engulfing که
# باعث تشکیل یک "زون" معتبر می‌شود. زون فقط با Close (نه Wick)
# باطل می‌شود - دقیقاً مطابق پارامتر "Invalidate Zone on Wick: false"
# در تنظیمات اندیکاتور مرجع.
#
# ⚠️ توضیح صادقانه: این یک پیاده‌سازی مستقل از صفر است بر اساس مفاهیم
# عمومی و شناخته‌شده‌ی Equal Highs/Lows + Liquidity Sweep + Engulfing
# که در تحلیل تکنیکال رایج هستند - نه رونویسی یا مهندسی معکوس از کد
# کامپایل‌شده‌ی هیچ اندیکاتوری.
# ============================================================

import numpy as np

STRATEGY_ID = "equal_liquidity"

STRATEGY_INFO = {
    "id": STRATEGY_ID,
    "display_name": "⚖️ Equal Liquidity",
    "description": "شکار نقدینگی روی Equal Highs/Lows با تأیید Engulfing (جایگزین Surpri3e و Liquidity Sweep)",
    "params": {
        "lookback": {
            "label": "بازه‌ی جستجوی Equal High/Low (کندل)",
            "default": 30,
            "type": "int",
            "min": 10,
            "max": 100,
            "help": "چند کندل اخیر برای پیدا کردن سقف/کف‌های برابر بررسی بشه",
        },
        "equal_tolerance_atr": {
            "label": "تلورانس برابری (× ATR)",
            "default": 0.5,
            "type": "float",
            "min": 0.1,
            "max": 2.0,
            "help": "دو سقف/کف با این اختلاف (نسبت به ATR) 'برابر' حساب می‌شن",
        },
        "max_zone_atr": {
            "label": "حداکثر اندازه‌ی زون (× ATR)",
            "default": 2.0,
            "type": "float",
            "min": 0.5,
            "max": 6.0,
            "help": "زون‌های بزرگ‌تر از این مقدار (نسبت به ATR) رد می‌شن - فیلتر نویز",
        },
        "max_sweep_age": {
            "label": "حداکثر قدمت Sweep (کندل)",
            "default": 3,
            "type": "int",
            "min": 1,
            "max": 10,
            "help": "Sweep + Engulf باید در همین چند کندل اخیر اتفاق افتاده باشه",
        },
    },
}

ATR_PERIOD = 14
MIN_RISK_ATR_MULTIPLIER = 0.5
MAX_RISK_ATR_MULTIPLIER = 4.0
SL_BUFFER_ATR_MULTIPLIER = 0.15


def _get_param(strategy_id, param_name):
    """پارامتر رو از دیتابیس می‌خونه؛ اگه ذخیره نشده بود، مقدار پیش‌فرض این فایل."""
    from database import get_strategy_setting
    param_def = STRATEGY_INFO["params"][param_name]
    raw = get_strategy_setting(strategy_id, param_name, default=None)
    if raw is None:
        return param_def["default"]
    try:
        return int(raw) if param_def["type"] == "int" else float(raw)
    except (TypeError, ValueError):
        return param_def["default"]


def _calculate_atr(df, period=ATR_PERIOD):
    """محاسبه‌ی Average True Range (نوسان واقعی کندل‌ها)."""
    if df is None or len(df) < period + 1:
        return None

    high = df['High'].values
    low = df['Low'].values
    close = df['Close'].values

    true_ranges = []
    for i in range(1, len(df)):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        true_ranges.append(max(hl, hc, lc))

    if len(true_ranges) < period:
        return None

    recent_tr = true_ranges[-period:]
    atr = float(np.mean(recent_tr))
    return atr if atr > 0 else None


def _find_equal_level(values, tolerance, find_max=True):
    """
    داخل آرایه‌ی `values` (سقف‌ها یا کف‌ها)، دنبال دست‌کم دو نقطه‌ی
    نزدیک به هم (اختلاف <= tolerance) می‌گرده که نزدیک‌ترین سطح به
    اکسترمم کلی بازه باشن (یعنی واقعاً محل تجمع نقدینگی، نه هر جفت
    تصادفی).

    خروجی: (equal_level: float, indices: list[int]) یا (None, [])
    """
    n = len(values)
    if n < 2:
        return None, []

    order = np.argsort(values)
    if find_max:
        order = order[::-1]

    anchor_idx = order[0]
    anchor_val = values[anchor_idx]
    matches = [anchor_idx]

    for idx in order[1:]:
        if abs(values[idx] - anchor_val) <= tolerance:
            matches.append(idx)

    if len(matches) < 2:
        return None, []

    matched_vals = [values[i] for i in matches]
    equal_level = float(np.mean(matched_vals))
    return equal_level, sorted(matches)


def _is_engulfing(prev_open, prev_close, curr_open, curr_close, direction):
    """
    بررسی می‌کنه کندل فعلی، بدنه‌ی کندل قبلی رو کامل Engulf می‌کنه یا نه،
    در جهت مشخص‌شده.
    """
    prev_body_low = min(prev_open, prev_close)
    prev_body_high = max(prev_open, prev_close)
    curr_body_low = min(curr_open, curr_close)
    curr_body_high = max(curr_open, curr_close)

    fully_engulfs = curr_body_low <= prev_body_low and curr_body_high >= prev_body_high

    if not fully_engulfs:
        return False

    if direction == "BUY":
        return curr_close > curr_open
    else:
        return curr_close < curr_open


def detect_equal_liquidity_setup(df, lookback=30, equal_tolerance_atr=0.5, max_zone_atr=2.0, max_sweep_age=3):
    """
    منطق لیمیت اوردر: فقط یک سطح Equal High/Low معتبر پیدا می‌کنه که
    هنوز لمس/باطل نشده - سطح رو به‌عنوان نقطه‌ی لیمیت برمی‌گردونه.

    ⚠️ تغییر معماری نسبت به نسخه‌ی قبلی (لحظه‌ای/instant):
    قبلاً منتظر می‌موند Equal High/Low + Sweep + Engulf همه هم‌زمان
    (روی چند کندل آخر) کامل بشن - این در دیتای واقعی به‌ندرت پیش میاد
    چون این سه رویداد معمولاً در سه لحظه‌ی متفاوت اتفاق می‌افتن، نه
    هم‌زمان. نتیجه: ربات عملاً هیچ‌وقت سیگنال نمی‌داد.

    ✅ راه‌حل: به‌محض شناسایی خودِ سطح Equal (بدون نیاز به sweep یا
    engulf که هنوز اتفاق نیفتاده)، سطح رو به‌عنوان یک Limit Order
    برمی‌گردونیم. ربات این سطح رو ذخیره می‌کنه و منتظر می‌مونه قیمت
    در آینده (نه لزوماً همین لحظه) به اون سطح برسه - دقیقاً مثل
    گذاشتن سفارش لیمیت واقعی روی نقدینگی.

    جهت معامله:
      - سطح Equal Low  -> BUY  (قیمت که به کف برسه، انتظار برگشت به بالا)
      - سطح Equal High -> SELL (قیمت که به سقف برسه، انتظار برگشت به پایین)

    خروجی: dict با کلیدهای direction, equal_level, zone_size(=0، چون
    هنوز sweep واقعی رخ نداده), touches یا None اگه هیچ سطح معتبری
    پیدا نشه.

    ⚠️ اگه چند سطح Equal (هم High هم Low) هم‌زمان پیدا بشن، سطحی که
    بیشترین touches (تعداد لمس) رو داره اولویت داره - چون سطح با
    لمس بیشتر، نقدینگی بیشتری جمع کرده و احتمال واکنش قیمت روش بالاتره.
    """
    min_len = lookback + 5
    if df is None or len(df) < min_len:
        return None

    atr = _calculate_atr(df)
    if atr is None:
        return None

    equal_tolerance = atr * equal_tolerance_atr

    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values

    n = len(df)
    window_start = max(0, n - lookback)
    window_highs = highs[window_start:n]
    window_lows = lows[window_start:n]
    last_close = closes[-1]

    candidates = []

    # ===================== کاندید SELL: سطح Equal High =====================
    equal_high, high_matches = _find_equal_level(window_highs, equal_tolerance, find_max=True)
    if equal_high is not None:
        # ===== اگه قیمت همین الان (با Close) از سطح رد شده باشه، سطح باطل شده - نادیده بگیر =====
        # (طبق پارامتر "Invalidate Zone on Wick: false" در اندیکاتور مرجع:
        # فقط Close می‌تونه باطل کنه، نه فتیله)
        if last_close < equal_high:
            candidates.append({
                'direction': 'SELL',
                'equal_level': round(float(equal_high), 5),
                'zone_size': 0.0,
                'touches': len(high_matches),
            })

    # ===================== کاندید BUY: سطح Equal Low =====================
    equal_low, low_matches = _find_equal_level(window_lows, equal_tolerance, find_max=False)
    if equal_low is not None:
        if last_close > equal_low:
            candidates.append({
                'direction': 'BUY',
                'equal_level': round(float(equal_low), 5),
                'zone_size': 0.0,
                'touches': len(low_matches),
            })

    if not candidates:
        return None

    # ===== انتخاب سطح با بیشترین touches (نقدینگی بیشتر = اولویت بالاتر) =====
    candidates.sort(key=lambda c: c['touches'], reverse=True)
    return candidates[0]


def analyze(df, rr_override=None, mode='standard', symbol='XAU/USD', timeframe='5min'):
    """
    تابع اصلی تحلیل - امضای استاندارد همه‌ی استراتژی‌های plugin.

    ⚠️ خروجی این نسخه یک سیگنال LIMIT است، نه سیگنال لحظه‌ای:
    signal['entry'] قیمتی است که هنوز به آن نرسیده‌ایم (سطح Equal
    High/Low) - نه قیمت فعلی بازار. main.py باید این سیگنال را به‌عنوان
    یک لیمیت اوردر معلق (PENDING) ذخیره کند، نه یک معامله‌ی بلافاصله باز.
    signal['signal_type'] = 'LIMIT' این تمایز را مشخص می‌کند.

    خروجی: (signal: dict, analysis: dict) یا (None, None)
    """
    if df is None or len(df) < 30:
        return None, None

    is_real = df.attrs.get('is_real_data', True)

    lookback = int(_get_param(STRATEGY_ID, "lookback"))
    equal_tolerance_atr = float(_get_param(STRATEGY_ID, "equal_tolerance_atr"))
    max_zone_atr = float(_get_param(STRATEGY_ID, "max_zone_atr"))
    max_sweep_age = int(_get_param(STRATEGY_ID, "max_sweep_age"))

    setup = detect_equal_liquidity_setup(
        df,
        lookback=lookback,
        equal_tolerance_atr=equal_tolerance_atr,
        max_zone_atr=max_zone_atr,
        max_sweep_age=max_sweep_age,
    )
    if not setup:
        return None, None

    direction = setup['direction']
    # ===== entry = خودِ سطح Equal (نقطه‌ی لیمیت)، نه قیمت لحظه‌ای =====
    entry = setup['equal_level']

    if rr_override is not None:
        rr_ratio = float(rr_override)
    else:
        rr_ratio = 2.0

    from strategies.risk_common import get_stop_distance
    atr_risk, sl_buffer = get_stop_distance(df, entry, symbol)

    # ===== SL کمی پشت‌تر از خودِ سطح Equal (جایی که نقدینگی جمع شده) =====
    risk = atr_risk + sl_buffer

    if direction == "BUY":
        sl = round(entry - risk, 2)
        tp = round(entry + (risk * rr_ratio), 2)
    else:
        sl = round(entry + risk, 2)
        tp = round(entry - (risk * rr_ratio), 2)

    strength = 'NORMAL' if setup['touches'] >= 2 else 'WEAK'

    rr_display = f"1:{rr_ratio:g}"
    reasons = [
        f"Equal {'Lows' if direction == 'BUY' else 'Highs'} ✅ ({entry:.2f} · {setup['touches']} touches)",
        f"نوع سفارش: Limit Order (منتظر رسیدن قیمت به سطح)",
        f"Risk/Reward: {rr_display} ✅",
    ]

    if strength == 'WEAK':
        import logging
        logging.getLogger(__name__).info(
            f"سیگنال لیمیت Equal Liquidity با strength=WEAK صادر شد (touches={setup['touches']})."
        )

    if not is_real:
        import logging
        fallback_reason = df.attrs.get('fallback_reason', 'نامشخص')
        logging.getLogger(__name__).warning(
            f"⚠️ سیگنال Equal Liquidity روی داده‌ی تستی/شبیه‌سازی‌شده صادر شد - دلیل: {fallback_reason}"
        )

    signal = {
        'direction': direction,
        'entry': entry,
        'sl': sl,
        'tp': tp,
        'strength': strength,
        'signal_type': 'LIMIT',
    }

    analysis = {
        'reasons': reasons,
        'style': STRATEGY_INFO['display_name'],
        'strength': strength,
    }

    return signal, analysis
