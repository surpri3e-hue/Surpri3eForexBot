# ============================================================
# 📁 strategies/liquidity_sweep.py
# 📌 استراتژی Liquidity Sweep - بر اساس مفاهیم سند «شکار جریان نقدینگی
#    در بازار» (مترجم: آرش سرابی)
# 📅 نسخه‌ی اول: 2026-07-21
#
# ⚠️ توضیح صادقانه درباره‌ی دامنه‌ی این پیاده‌سازی:
# سند منبع بیشتر توصیفی/آموزشیه (رفتار بانک‌ها، جنگ روانی، اخبار
# فاندامنتال) که قابل تبدیل به قانون قیمتیِ قابل‌اندازه‌گیری نیست - آن
# بخش‌ها عمداً پیاده‌سازی نشدن. چیزی که این فایل واقعاً پیاده‌سازی می‌کنه
# دقیقاً همون هسته‌ی قابل‌سنجش سند است:
#
#   1) Liquidity Sweep (شکار استاپ / شکست کاذب):
#      قیمت با فتیله‌ی یک کندل از یک سطح سویینگ قبلی (High یا Low) عبور
#      می‌کنه - یعنی سفارشات/استاپ‌های پشت اون سطح "برداشته" می‌شن - ولی
#      بدنه‌ی همون کندل (Close) داخل رنج قبلی برمی‌گرده. طبق سند، این
#      نشونه‌ی برداشتن نقدینگی است، نه شکست واقعی؛ جهت واقعی، برعکسِ
#      جهت شکستِ ظاهریه.
#
#   2) تایید تایم‌فریم بالاتر (مهم‌ترین توصیه‌ی صریح سند: «اساسی‌ترین
#      نکته این است که در بررسی جریان نقدینگی همیشه به یک تایم فریم
#      بالاتر رجوع کنید تا در دام کندل‌های برگشتی جعلی نیفتید»):
#      سیگنال فقط زمانی صادر می‌شه که جهت آن، با روند کلیِ یک تایم‌فریم
#      بزرگ‌تر (که این فایل خودش جداگانه می‌گیره) هم‌راستا باشه.
# ============================================================

import numpy as np

STRATEGY_ID = "liquidity_sweep"

STRATEGY_INFO = {
    "id": STRATEGY_ID,
    "display_name": "🌊 Liquidity Sweep",
    "description": "شکار نقدینگی/استاپ‌هانت با تایید روند تایم‌فریم بالاتر (بر اساس سند شکار جریان نقدینگی)",
    "params": {
        "swing_lookback": {
            "label": "بازه‌ی تشخیص سطح سویینگ (کندل)",
            "default": 20,
            "type": "int",
            "min": 5,
            "max": 60,
            "help": "چند کندل اخیر برای پیدا کردن بالاترین/پایین‌ترین سطح سویینگ بررسی بشه",
        },
        "max_sweep_age": {
            "label": "حداکثر قدمت Sweep (کندل)",
            "default": 3,
            "type": "int",
            "min": 1,
            "max": 10,
            "help": "Sweep باید در همین چند کندل اخیر اتفاق افتاده باشه تا معتبر باشه",
        },
        "min_wick_ratio": {
            "label": "حداقل نسبت فتیله به بدنه",
            "default": 1.5,
            "type": "float",
            "min": 1.0,
            "max": 5.0,
            "help": "فتیله‌ی sweep باید حداقل این‌قدر برابر بدنه‌ی کندل باشه (فتیله‌ی بزرگ = شکار قوی‌تر)",
        },
    },
}

# ===== نگاشت تایم‌فریم فعلی به یک تایم‌فریم بزرگ‌تر، برای تایید روند =====
# طبق توصیه‌ی صریح سند: «همیشه به یک تایم‌فریم بالاتر رجوع کنید»
HIGHER_TIMEFRAME_MAP = {
    "1min": "15min",
    "5min": "1h",
    "15min": "4h",
    "30min": "4h",
    "1h": "4h",
    "4h": "1d",
    "1d": "1d",  # از قبل بزرگ‌ترینه - همون رو نگه می‌داریم
}

# ===== همون منطق ریسک نسبی به ATR که در استراتژی ZigZag جواب داد =====
ATR_PERIOD = 14
MIN_RISK_ATR_MULTIPLIER = 0.5
MAX_RISK_ATR_MULTIPLIER = 4.0
SL_BUFFER_ATR_MULTIPLIER = 0.15  # کمی بزرگ‌تر از zigzag چون SL باید پشت سطح sweep شده باشه

SCALP_TARGET_CANDLES = 5
SCALP_MOVE_LOOKBACK = 20

FALLBACK_MIN_RISK_PERCENT = 0.0005
FALLBACK_MAX_RISK_PERCENT = 0.02
FALLBACK_SL_BUFFER_PERCENT = 0.0002


def _get_param(strategy_id, param_name):
    """پارامتر رو از دیتابیس می‌خونه؛ اگه ذخیره نشده بود، مقدار پیش‌فرض این فایل."""
    from database import get_strategy_setting
    default = STRATEGY_INFO["params"][param_name]["default"]
    param_type = STRATEGY_INFO["params"][param_name]["type"]
    raw = get_strategy_setting(strategy_id, param_name, default=None)
    if raw is None:
        return default
    try:
        return int(raw) if param_type == "int" else float(raw)
    except (TypeError, ValueError):
        return default


def _calculate_atr(df, period=ATR_PERIOD):
    """همون تابع محاسبه‌ی ATR که در surpri3e_zigzag.py استفاده شد (نوسان واقعی کندل‌ها)."""
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


def _estimate_scalp_max_distance(df, target_candles=SCALP_TARGET_CANDLES, lookback=SCALP_MOVE_LOOKBACK):
    """همون تابع تخمین سرعت حرکت قیمت که در surpri3e_zigzag.py برای اسکلپ استفاده شد."""
    if df is None or len(df) < lookback + 1:
        return None

    close = df['Close'].values[-(lookback + 1):]
    moves = np.abs(np.diff(close))
    if len(moves) == 0:
        return None

    avg_move_per_candle = float(np.mean(moves))
    if avg_move_per_candle <= 0:
        return None

    return avg_move_per_candle * target_candles


def detect_liquidity_sweep(df, swing_lookback=20, max_sweep_age=3, min_wick_ratio=1.5):
    """
    دنبال یک Liquidity Sweep معتبر می‌گرده:
      - یک سطح سویینگ (بالاترین High یا پایین‌ترین Low) در `swing_lookback`
        کندل قبل از ناحیه‌ی بررسی پیدا می‌شه.
      - در یکی از `max_sweep_age` کندل اخیر، فتیله‌ی کندل از اون سطح رد
        شده (یعنی نقدینگی/استاپ‌های پشت سطح "برداشته" شدن).
      - اما بدنه‌ی همون کندل (Close) داخل سطح برگشته - یعنی رد شدن فتیله
        یک شکست واقعی نبوده، بلکه شکار نقدینگی بوده.
      - نسبت فتیله به بدنه باید حداقل min_wick_ratio باشه (فتیله‌ی
        قابل‌توجه، نه نویز کوچیک).

    خروجی: dict با کلیدهای:
        direction: 'BUY' (اگه sweep زیر یک Low بوده - یعنی sell-side
                   liquidity گرفته شده و برگشت صعودیه) یا 'SELL' (اگه
                   sweep بالای یک High بوده)
        swept_level: قیمت سطحی که sweep شده
        sweep_candle_index: اندیس کندلی که sweep توش اتفاق افتاده
        wick_ratio: نسبت فتیله به بدنه‌ی همون کندل
    یا None اگه هیچ sweep معتبری پیدا نشه.
    """
    if df is None or len(df) < swing_lookback + max_sweep_age + 2:
        return None

    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    opens = df['Open'].values if 'Open' in df.columns else closes  # fallback اگه Open نبود

    n = len(df)

    # ===== بررسی هر کندل در بازه‌ی max_sweep_age اخیر (از جدید به قدیم) =====
    for candles_ago in range(1, max_sweep_age + 1):
        idx = n - candles_ago
        if idx < swing_lookback:
            continue

        # ===== سطح سویینگ رو از قبل از این کندل (نه شامل خودش) پیدا می‌کنیم =====
        window_start = max(0, idx - swing_lookback)
        prior_highs = highs[window_start:idx]
        prior_lows = lows[window_start:idx]
        if len(prior_highs) == 0:
            continue

        swing_high = float(np.max(prior_highs))
        swing_low = float(np.min(prior_lows))

        candle_high = highs[idx]
        candle_low = lows[idx]
        candle_close = closes[idx]
        candle_open = opens[idx]

        body_size = abs(candle_close - candle_open)
        if body_size <= 0:
            body_size = (candle_high - candle_low) * 0.1  # جلوگیری از تقسیم بر صفر برای دوجی‌ها

        # ===== Sweep بالای سطح High قبلی (شکار buy-side liquidity => برگشت SELL) =====
        upper_wick = candle_high - max(candle_close, candle_open)
        if candle_high > swing_high and candle_close < swing_high:
            wick_ratio = upper_wick / body_size if body_size > 0 else 0
            if wick_ratio >= min_wick_ratio:
                return {
                    'direction': 'SELL',
                    'swept_level': swing_high,
                    'sweep_candle_index': idx,
                    'sweep_candles_ago': candles_ago,
                    'wick_ratio': round(wick_ratio, 2),
                }

        # ===== Sweep پایین سطح Low قبلی (شکار sell-side liquidity => برگشت BUY) =====
        lower_wick = min(candle_close, candle_open) - candle_low
        if candle_low < swing_low and candle_close > swing_low:
            wick_ratio = lower_wick / body_size if body_size > 0 else 0
            if wick_ratio >= min_wick_ratio:
                return {
                    'direction': 'BUY',
                    'swept_level': swing_low,
                    'sweep_candle_index': idx,
                    'sweep_candles_ago': candles_ago,
                    'wick_ratio': round(wick_ratio, 2),
                }

    return None


def get_higher_timeframe_trend(symbol, timeframe):
    """
    دیتای یک تایم‌فریم بزرگ‌تر رو می‌گیره و جهت روند کلی‌اش رو تشخیص می‌ده.
    این دقیقاً همون توصیه‌ی اصلی سند است: تایید سیگنال sweep با تایم‌فریم بالاتر.

    روند با مقایسه‌ی میانگین ۱۰ کندل اخیر با ۱۰ کندل قبل از اون تشخیص داده
    می‌شه - یک روش ساده و قابل‌اتکا برای گرفتن جهت کلی بدون نیاز به
    اندیکاتور پیچیده.

    خروجی: 'BUY' (روند صعودی)، 'SELL' (روند نزولی)، یا None (تشخیص ممکن نشد)
    """
    higher_tf = HIGHER_TIMEFRAME_MAP.get(timeframe, "4h")

    try:
        from market import get_gold_candles
        htf_df = get_gold_candles(higher_tf, symbol=symbol)
    except Exception:
        return None

    if htf_df is None or len(htf_df) < 25:
        return None

    closes = htf_df['Close'].values
    recent_avg = float(np.mean(closes[-10:]))
    prior_avg = float(np.mean(closes[-20:-10]))

    if recent_avg > prior_avg:
        return 'BUY'
    elif recent_avg < prior_avg:
        return 'SELL'
    return None


def analyze(df, rr_override=None, mode='standard', symbol='XAU/USD', timeframe='5min'):
    """
    تابع اصلی تحلیل - امضای استاندارد همه‌ی استراتژی‌های plugin.

    منطق: یک Liquidity Sweep معتبر پیدا می‌کنه، و فقط در صورتی سیگنال
    صادر می‌کنه که جهتش با روند تایم‌فریم بالاتر هم‌راستا باشه (طبق
    توصیه‌ی اصلی سند منبع).

    خروجی: (signal: dict, analysis: dict) یا (None, None)
    """
    if df is None or len(df) < 30:
        return None, None

    is_real = df.attrs.get('is_real_data', True)

    swing_lookback = int(_get_param(STRATEGY_ID, "swing_lookback"))
    max_sweep_age = int(_get_param(STRATEGY_ID, "max_sweep_age"))
    min_wick_ratio = float(_get_param(STRATEGY_ID, "min_wick_ratio"))

    sweep = detect_liquidity_sweep(df, swing_lookback=swing_lookback, max_sweep_age=max_sweep_age, min_wick_ratio=min_wick_ratio)
    if not sweep:
        return None, None

    # ===== تایید تایم‌فریم بالاتر - قلب اصلی این استراتژی طبق سند منبع =====
    htf_trend = get_higher_timeframe_trend(symbol, timeframe)
    if htf_trend is None or htf_trend != sweep['direction']:
        # ===== جهت sweep با روند تایم‌فریم بالاتر هم‌راستا نیست - از سند: =====
        # ===== «همیشه به یک تایم‌فریم بالاتر رجوع کنید تا در دام کندل‌های =====
        # ===== برگشتی جعلی نیفتید» - پس این ستاپ رو نادیده می‌گیریم. =====
        return None, None

    direction = sweep['direction']
    current = float(df['Close'].iloc[-1])
    entry = round(current, 2)

    if rr_override is not None:
        rr_ratio = float(rr_override)
    else:
        rr_ratio = 2.0

    # ===== فاصله‌ی استاپ: خودکار بر اساس نوسان واقعی بازار (ATR) =====
    from strategies.risk_common import get_stop_distance
    atr_risk, sl_buffer = get_stop_distance(df, entry, symbol)

    # ===== SL منطقی‌ترین جا: کمی پشت سطح sweep شده (جایی که نقدینگی گرفته شد) =====
    swept_level = sweep['swept_level']
    if direction == "BUY":
        swept_based_risk = entry - (swept_level - sl_buffer)
    else:
        swept_based_risk = (swept_level + sl_buffer) - entry

    # ===== فاصله‌ی نهایی: بزرگ‌تر از (فاصله‌ی سطح sweep شده، حداقل ATR) =====
    risk = max(swept_based_risk, atr_risk)

    if direction == "BUY":
        sl = round(entry - risk, 2)
        tp = round(entry + (risk * rr_ratio), 2)
    else:
        sl = round(entry + risk, 2)
        tp = round(entry - (risk * rr_ratio), 2)

    strength = 'NORMAL' if sweep['sweep_candles_ago'] <= 2 else 'WEAK'

    rr_display = f"1:{rr_ratio:g}"
    reasons = [
        f"Liquidity Sweep ✅ ({sweep['swept_level']:.2f} · wick/body {sweep['wick_ratio']}x)",
        f"Higher Timeframe Confirmation ✅ ({HIGHER_TIMEFRAME_MAP.get(timeframe, '4h')})",
        f"Signal Strength: {strength} ✅",
        f"Risk/Reward: {rr_display} ✅",
    ]

    if strength == 'WEAK':
        import logging
        logging.getLogger(__name__).info(
            f"سیگنال Liquidity Sweep با strength=WEAK صادر شد (sweep {sweep['sweep_candles_ago']} کندل قبل)."
        )

    if not is_real:
        import logging
        fallback_reason = df.attrs.get('fallback_reason', 'نامشخص')
        logging.getLogger(__name__).warning(
            f"⚠️ سیگنال Liquidity Sweep روی داده‌ی تستی/شبیه‌سازی‌شده صادر شد - دلیل: {fallback_reason}"
        )

    signal = {
        'direction': direction,
        'entry': entry,
        'sl': sl,
        'tp': tp,
        'strength': strength,
    }

    analysis = {
        'reasons': reasons,
        'style': STRATEGY_INFO['display_name'],
        'strength': strength,
    }

    return signal, analysis
