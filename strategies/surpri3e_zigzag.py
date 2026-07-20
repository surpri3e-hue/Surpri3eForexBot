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

# ============================================================
# ⚠️ رفع باگ مهم (۲۰۲۶-۰۷-۱۹): قبلاً MIN_RISK/MAX_RISK به‌صورت دلاری
# ثابت (۲ تا ۱۵ دلار) تعریف شده بودن که فقط برای مقیاس قیمتی طلا
# (XAU/USD ~ 4000$) منطقی بود. این باعث می‌شد روی BTC/USD (قیمت ~۶۵۰۰۰$)
# که تغییرات قیمتی خیلی بزرگ‌تری داره، SL/TP همیشه به این کلمپ ثابت
# بچسبه.
#
# ⚠️ رفع باگ تکمیلی (گزارش کاربر): حتی بعد از تبدیل به درصد قیمت،
# باگ روی *همه‌ی* تایم‌فریم‌ها اثر داشت - نه فقط ۴ ساعته. چون درصد ثابت
# (۰.۰۵٪ تا ۲٪) برای هر تایم‌فریمی یکسان بود، در حالی که نوسان طبیعی
# قیمت در کندل‌های ۱ روزه به‌مراتب بیشتر از کندل‌های ۱ دقیقه‌ایه - نتیجه
# این بود که SL/TP در تایم‌فریم‌های بزرگ‌تر هم بیش‌ازحد نزدیک به entry
# می‌موند (چسبیده به سقف/کف درصدی که برای تایم‌فریم‌های کوچیک منطقی بود).
#
# ✅ راه‌حل نهایی: به‌جای درصد ثابت، از ATR واقعی (Average True Range)
# خود کندل‌های همون تایم‌فریم استفاده می‌شه. ATR مستقیماً نشون می‌ده هر
# کندل تو اون تایم‌فریم و اون نماد به‌طور میانگین چقدر نوسان داره - پس
# خودکار و دقیق با هر ترکیب نماد/تایم‌فریمی سازگار می‌شه، بدون نیاز به
# جدول یا ضریب دستی.
# ============================================================
ATR_PERIOD = 14             # تعداد کندل برای محاسبه‌ی میانگین ATR (استاندارد صنعتی)
MIN_RISK_ATR_MULTIPLIER = 0.5   # کف ریسک: حداقل نصف ATR
MAX_RISK_ATR_MULTIPLIER = 4.0   # سقف ریسک: حداکثر ۴ برابر ATR
SL_BUFFER_ATR_MULTIPLIER = 0.1  # فاصله‌ی اطمینان اضافه: ۱۰٪ ATR

# ===== fallback در صورتی که ATR قابل محاسبه نباشه (دیتای خیلی کوتاه) =====
FALLBACK_MIN_RISK_PERCENT = 0.0005
FALLBACK_MAX_RISK_PERCENT = 0.02
FALLBACK_SL_BUFFER_PERCENT = 0.0001

# ============================================================
# ⚠️ رفع باگ گزارش‌شده: مود Fast Scalp (تایم‌فریم ۱ دقیقه) باید واقعاً
# ظرف چند دقیقه به TP/SL برسه - نه بعد از ساعت‌ها (که دیگه اسکلپ حساب
# نمی‌شه، عملاً مثل Standard رفتار می‌کرد). چون ATR روی ۱۴ کندل حساب
# می‌شه (یعنی ~۱۴ دقیقه‌ی گذشته)، فاصله‌ی حاصل از اون به‌تنهایی می‌تونست
# طوری بزرگ بشه که رسیدن قیمت بهش خیلی بیشتر از ۵ دقیقه طول بکشه.
#
# ✅ راه‌حل: برای مود اسکلپ، یک سقف اضافه بر مبنای «میانگین حرکت قیمت
# در SCALP_TARGET_CANDLES کندل اخیر» روی max_risk اعمال می‌شه. این
# مستقیماً نشون می‌ده قیمت معمولاً ظرف همون تعداد کندل (که برای تایم‌فریم
# ۱ دقیقه‌ای اسکلپ می‌شه SCALP_TARGET_CANDLES دقیقه) چقدر واقعاً حرکت
# می‌کنه - و SL/TP رو به همون بازه‌ی واقعی محدود می‌کنه.
# ============================================================
SCALP_TARGET_CANDLES = 5        # هدف: رسیدن به TP/SL ظرف ۵ کندل (روی تایم‌فریم ۱ دقیقه = ۵ دقیقه)
SCALP_MOVE_LOOKBACK = 20        # تعداد کندل اخیر برای سنجش میانگین سرعت حرکت قیمت


def _calculate_atr(df, period=ATR_PERIOD):
    """
    محاسبه‌ی Average True Range روی دیتافریم کندلی.

    True Range هر کندل = بزرگترین مقدار از سه حالت:
      1. High - Low (دامنه‌ی خودِ کندل)
      2. |High - Close قبلی|
      3. |Low - Close قبلی|

    ATR = میانگین متحرک True Range روی `period` کندل اخیر.
    این معیار مستقیماً نوسان واقعی بازار رو تو همون تایم‌فریم و همون
    نماد نشون می‌ده - برخلاف درصد ثابت قیمت که برای هر تایم‌فریمی یکسانه.

    خروجی: عدد ATR (float) یا None اگه دیتا برای محاسبه کافی نباشه.
    """
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

    # میانگین ساده‌ی آخرین `period` مقدار True Range
    recent_tr = true_ranges[-period:]
    atr = float(np.mean(recent_tr))

    return atr if atr > 0 else None


def _estimate_scalp_max_distance(df, target_candles=SCALP_TARGET_CANDLES, lookback=SCALP_MOVE_LOOKBACK):
    """
    میانگین اندازه‌ی حرکت قیمت (بر حسب |Close - Close قبلی|) روی
    `lookback` کندل اخیر رو حساب می‌کنه، و از روی اون تخمین می‌زنه
    قیمت معمولاً ظرف `target_candles` کندل چقدر واقعی حرکت می‌کنه.

    این معیار مستقل از ATR است (که روی رنج هر کندل تمرکز داره)، و به‌جاش
    مستقیماً روی جابه‌جایی خالص قیمت در طول زمان تمرکز می‌کنه - دقیقاً
    همون چیزی که برای تضمین «SL/TP ظرف N کندل برسه» لازم داریم.

    خروجی: فاصله‌ی تخمینی (float) یا None اگه دیتا ناکافی باشه.
    """
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


def analyze(df, rr_override=None, mode='standard'):
    """
    تابع اصلی تحلیل - امضای استاندارد همه‌ی استراتژی‌های plugin.

    rr_override (float|None): اگه داده بشه (RR اختصاصی خود کاربر)،
        به‌جای RR سراسری تنظیمات ربات برای محاسبه‌ی SL/TP استفاده می‌شه.
        این رفع باگی است که قبلاً SL/TP واقعی همیشه با RR سراسری ساخته
        می‌شد، در حالی که به کاربر RR شخصی‌اش نمایش داده می‌شد (ناهم‌خوانی).

    mode (str): 'standard' یا 'fast_scalp'. در مود fast_scalp، فاصله‌ی
        SL/TP به‌گونه‌ای محدود می‌شه که قیمت واقعاً بتونه ظرف چند دقیقه
        (نه ساعت‌ها) بهش برسه - چون این باگ قبلاً باعث می‌شد اسکلپ روی
        طلا عملاً مثل Standard رفتار کنه (زمان رسیدن به TP/SL خیلی طولانی).

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

    if rr_override is not None:
        rr_ratio = float(rr_override)
    else:
        # ===== دیگه تنظیم سراسری rr_ratio وجود نداره (طبق تصمیم پروژه: =====
        # ===== RR کاملاً به انتخاب خود کاربر/ادمین برای هر مود سپرده شده) =====
        # این فقط یک fallback ایمن برای زمانیه که به هر دلیلی rr_override
        # پاس داده نشده (نباید در جریان عادی اتفاق بیفته).
        rr_ratio = 2.0

    entry = round(current, 2)

    # ===== فاصله‌ی اطمینان و کلمپ ریسک، بر اساس ATR واقعی همون کندل‌ها =====
    # این‌طوری چه روی طلا (~4000$) چه بیت‌کوین (~65000$)، و چه تایم‌فریم
    # ۱ دقیقه‌ای یا ۱ روزه، مقیاس ریسک با نوسان واقعی بازار هم‌خوانی داره.
    atr = _calculate_atr(df)

    if atr is not None:
        sl_buffer = atr * SL_BUFFER_ATR_MULTIPLIER
        min_risk = atr * MIN_RISK_ATR_MULTIPLIER
        max_risk = atr * MAX_RISK_ATR_MULTIPLIER
    else:
        # ===== fallback نادر: دیتای کافی برای ATR نیست =====
        sl_buffer = entry * FALLBACK_SL_BUFFER_PERCENT
        min_risk = entry * FALLBACK_MIN_RISK_PERCENT
        max_risk = entry * FALLBACK_MAX_RISK_PERCENT

    if direction == "BUY":
        raw_risk = entry - (zz['pivot_price'] - sl_buffer)
    else:
        raw_risk = (zz['pivot_price'] + sl_buffer) - entry

    risk = max(min_risk, min(max_risk, raw_risk))

    # ============================================================
    # ⚠️ رفع باگ گزارش‌شده: با RR=2 مود اسکلپ درست بود، ولی RR=3 باعث
    # می‌شد TP خیلی دور بشه و دیگه ظرف ۵ دقیقه قابل‌دسترس نباشه. علتش
    # این بود که محدودیت زمانی فقط روی «risk» (فاصله‌ی SL) اعمال می‌شد،
    # نه روی خودِ TP - و چون TP = risk × rr_ratio ساخته می‌شه، با RR
    # بزرگ‌تر، TP به‌طور خطی از محدودیت زمانی فراتر می‌رفت.
    #
    # ✅ راه‌حل: در مود اسکلپ، فاصله‌ی TP (که risk × rr_ratio است) هم باید
    # داخل همون سقف زمانی (scalp_max_distance) بمونه. اگه با RR درخواستی
    # از سقف فراتر بره، «risk» رو طوری کوچک‌تر می‌کنیم که TP دقیقاً روی
    # سقف زمانی بشینه - این‌طوری RR انتخابی کاربر حفظ می‌شه (نسبت SL:TP
    # عوض نمی‌شه) ولی کل معامله (هم SL هم TP) داخل بازه‌ی ۵ دقیقه‌ای می‌مونه.
    # ============================================================
    if mode == 'fast_scalp':
        scalp_max_distance = _estimate_scalp_max_distance(df)
        if scalp_max_distance is not None and scalp_max_distance > 0:
            implied_tp_distance = risk * rr_ratio
            if implied_tp_distance > scalp_max_distance:
                # ===== risk رو کوچک می‌کنیم تا TP دقیقاً روی سقف زمانی بشینه =====
                # ===== نسبت RR درخواستی کاربر دست‌نخورده می‌مونه =====
                # ⚠️ نکته‌ی مهم: کف این مقدار نباید از min_risk (که برای
                # حالت عادی/غیر-اسکلپ تعریف شده) بیاد - چون min_risk هیچ
                # ربطی به سقف زمانی نداره و می‌تونه از scalp_max_distance
                # بزرگ‌تر باشه (که دقیقاً باعث همین باگ می‌شد: risk دوباره
                # بالا کشیده می‌شد و از سقف زمانی رد می‌شد). به‌جاش فقط از
                # صفر/منفی شدن مطلق جلوگیری می‌کنیم.
                risk = max(scalp_max_distance / rr_ratio, entry * 0.00001)

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

    # ===== متن دلایل: فرمت حرفه‌ای با تیک انگلیسی - فقط موارد واقعاً محاسبه‌شده =====
    # (هشدارهای «سیگنال ضعیف» و «داده‌ی تستی» دیگه در متن نمایشی کاربر
    # نیستن - این‌ها فقط در لاگ سرور ثبت می‌شن تا خودِ کاربر نگران/گیج نشه
    # ولی اطلاعات دیباگ همچنان برای ادمین در دسترس بمونه)
    rr_display = f"1:{rr_ratio:g}"
    reasons = [
        f"Surpri3e ZigZag ✅ ({zz['pivot_price']:.2f} · {zz['bars_ago']} candles ago)",
        f"Signal Strength: {strength} ✅",
        f"Risk/Reward: {rr_display} ✅",
    ]

    if strength == 'WEAK':
        import logging
        logging.getLogger(__name__).info(
            f"سیگنال WEAK صادر شد (pivot {zz['bars_ago']} کندل قبل، آستانه {freshness_threshold})."
        )

    if not is_real:
        import logging
        fallback_reason = df.attrs.get('fallback_reason', 'نامشخص')
        logging.getLogger(__name__).warning(
            f"⚠️ سیگنال روی داده‌ی تستی/شبیه‌سازی‌شده صادر شد (نه قیمت واقعی بازار) - دلیل: {fallback_reason}"
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
        'style': STRATEGY_INFO["display_name"],
        'score': None,
        'strength': strength,
    }

    return signal, analysis
