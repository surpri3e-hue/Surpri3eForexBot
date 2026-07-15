# ============================================================
# 📁 ict_logic.py
# 📌 وظیفه: تحلیل بازار با سبک ICT (ساختار بازار، FVG، Order Block)
# 📅 بازنویسی: 2026-07-15
# ============================================================

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands
from ta.volume import VolumeWeightedAveragePrice

# آستانه‌ها: زیر این حد اصلاً سیگنال نمی‌دیم (نویز محض)
MIN_SCORE_WEAK = 15
# بین MIN_SCORE_WEAK و این عدد: سیگنال ضعیف با هشدار
MIN_SCORE_NORMAL = 30


def analyze_ict(df):
    """
    تحلیل ICT (ساختار بازار BOS/MSS، FVG، Order Block، Liquidity)
    + اندیکاتورهای تکمیلی (RSI, MACD, EMA, Bollinger, VWAP)

    قوانین سیگنال‌دهی:
        امتیاز >= 30  -> سیگنال عادی
        15 <= امتیاز < 30 -> سیگنال ضعیف (با برچسب هشدار)
        امتیاز < 15  -> هیچ سیگنالی (None, None)

    ⚠️ هیچ fallback مبتنی بر نویز قیمت لحظه‌ای وجود ندارد.
    اگر ساختار بازار یا اندیکاتورها امتیاز کافی ندهند، سیگنالی صادر نمی‌شود.
    """
    if df is None or len(df) < 30:
        return None, None

    # ===== هشدار اگر روی دیتای تستی/شبیه‌سازی‌شده کار می‌کنیم =====
    is_real = df.attrs.get('is_real_data', True)  # پیش‌فرض True برای سازگاری با دیتافریم‌های بدون این پرچم

    df_copy = df.copy()

    # ===== اندیکاتورها =====
    rsi = RSIIndicator(close=df_copy['Close'], window=14)
    df_copy['rsi'] = rsi.rsi()

    macd = MACD(close=df_copy['Close'])
    df_copy['macd'] = macd.macd()
    df_copy['macd_signal'] = macd.macd_signal()

    df_copy['ema9'] = EMAIndicator(close=df_copy['Close'], window=9).ema_indicator()
    df_copy['ema21'] = EMAIndicator(close=df_copy['Close'], window=21).ema_indicator()
    df_copy['ema50'] = EMAIndicator(close=df_copy['Close'], window=50).ema_indicator()

    bb = BollingerBands(close=df_copy['Close'], window=20, window_dev=2)
    df_copy['bb_low'] = bb.bollinger_lband()
    df_copy['bb_high'] = bb.bollinger_hband()
    df_copy['bb_mid'] = bb.bollinger_mavg()

    vwap = VolumeWeightedAveragePrice(
        high=df_copy['High'], low=df_copy['Low'],
        close=df_copy['Close'], volume=df_copy['Volume']
    )
    df_copy['vwap'] = vwap.volume_weighted_average_price()

    current = df_copy['Close'].iloc[-1]
    current_rsi = df_copy['rsi'].iloc[-1]
    current_macd = df_copy['macd'].iloc[-1]
    current_macd_signal = df_copy['macd_signal'].iloc[-1]
    current_ema21 = df_copy['ema21'].iloc[-1]
    current_ema50 = df_copy['ema50'].iloc[-1]
    current_bb_low = df_copy['bb_low'].iloc[-1]
    current_bb_high = df_copy['bb_high'].iloc[-1]
    current_vwap = df_copy['vwap'].iloc[-1]

    # اگه هرکدوم از اندیکاتورها هنوز NaN باشن (داده کافی نیست)، صادقانه هیچی برنگردون
    critical_values = [current_rsi, current_macd, current_macd_signal, current_ema21, current_ema50, current_vwap]
    if any(pd.isna(v) for v in critical_values):
        return None, None

    close = df_copy['Close'].values
    high = df_copy['High'].values
    low = df_copy['Low'].values
    open_price = df_copy['Open'].values

    ict_buy_score = 0
    ict_buy_reasons = []
    ict_sell_score = 0
    ict_sell_reasons = []

    # ===== BOS (Break of Structure) =====
    bos_up = False
    bos_down = False
    if len(high) >= 10:
        last_high = max(high[-6:-1])
        last_low = min(low[-6:-1])
        if current > last_high and high[-1] > last_high:
            bos_up = True
        if current < last_low and low[-1] < last_low:
            bos_down = True

    if bos_up:
        ict_buy_score += 30
        ict_buy_reasons.append(f"شکست ساختار صعودی (BOS) بالای سطح {last_high:.2f}")
    if bos_down:
        ict_sell_score += 30
        ict_sell_reasons.append(f"شکست ساختار نزولی (BOS) پایین سطح {last_low:.2f}")

    # ===== MSS (Market Structure Shift) =====
    mss_up = False
    mss_down = False
    if len(high) >= 15:
        prev_high = max(high[-15:-5])
        prev_low = min(low[-15:-5])
        if current > prev_high and low[-1] > prev_low:
            mss_up = True
        if current < prev_low and high[-1] < prev_high:
            mss_down = True

    if mss_up:
        ict_buy_score += 25
        ict_buy_reasons.append("تغییر ساختار بازار (MSS) در جهت صعودی")
    if mss_down:
        ict_sell_score += 25
        ict_sell_reasons.append("تغییر ساختار بازار (MSS) در جهت نزولی")

    # ===== FVG (Fair Value Gap) - سه‌کندلی، جهت اصلاح‌شده =====
    # Bullish FVG: low کندل جدیدتر (i+1) بالاتر از high کندل قدیمی‌تر (i-1) باشه
    # Bearish FVG: high کندل جدیدتر (i+1) پایین‌تر از low کندل قدیمی‌تر (i-1) باشه
    fvg_up = None
    fvg_down = None
    if len(df) >= 5:
        for i in range(len(df) - 2, 0, -1):
            if low[i + 1] > high[i - 1]:
                fvg_up = {'upper': low[i + 1], 'lower': high[i - 1]}
                break
            if high[i + 1] < low[i - 1]:
                fvg_down = {'upper': low[i - 1], 'lower': high[i + 1]}
                break

    if fvg_up:
        ict_buy_score += 25
        ict_buy_reasons.append(f"شکاف قیمتی نامتعادل (FVG) صعودی در محدوده {fvg_up['lower']:.2f}–{fvg_up['upper']:.2f}")
    if fvg_down:
        ict_sell_score += 25
        ict_sell_reasons.append(f"شکاف قیمتی نامتعادل (FVG) نزولی در محدوده {fvg_down['lower']:.2f}–{fvg_down['upper']:.2f}")

    # ===== Order Block =====
    buy_ob = None
    sell_ob = None
    if len(df) >= 15:
        for i in range(len(df) - 3, 0, -1):
            if close[i] < open_price[i] and close[i + 1] > high[i]:
                buy_ob = {'price': high[i]}
                break
        for i in range(len(df) - 3, 0, -1):
            if close[i] > open_price[i] and close[i + 1] < low[i]:
                sell_ob = {'price': low[i]}
                break

    if buy_ob:
        ict_buy_score += 25
        ict_buy_reasons.append(f"ناحیه‌ی سفارش نهادی (Order Block) خرید در محدوده‌ی {buy_ob['price']:.2f}")
    if sell_ob:
        ict_sell_score += 25
        ict_sell_reasons.append(f"ناحیه‌ی سفارش نهادی (Order Block) فروش در محدوده‌ی {sell_ob['price']:.2f}")

    # ===== Liquidity =====
    buy_liquidity = False
    sell_liquidity = False
    if len(high) >= 20:
        recent_highs = high[-20:]
        recent_lows = low[-20:]
        if current > max(recent_highs) - 2:
            buy_liquidity = True
        if current < min(recent_lows) + 2:
            sell_liquidity = True

    if buy_liquidity:
        ict_buy_score += 15
        ict_buy_reasons.append("نزدیکی به منطقه‌ی نقدینگی خریداران")
    if sell_liquidity:
        ict_sell_score += 15
        ict_sell_reasons.append("نزدیکی به منطقه‌ی نقدینگی فروشندگان")

    # ===== ZigZag (لایه‌ی تاییدی از اندیکاتور نقاط چرخش) =====
    from zigzag_logic import get_zigzag_signal
    zz = get_zigzag_signal(df)
    if zz:
        if zz['direction'] == 'BUY':
            ict_buy_score += 25
            ict_buy_reasons.append(
                f"تایید نقطه‌ی چرخش ZigZag در جهت صعودی (سطح {zz['pivot_price']:.2f}، {zz['bars_ago']} کندل قبل)"
            )
        else:
            ict_sell_score += 25
            ict_sell_reasons.append(
                f"تایید نقطه‌ی چرخش ZigZag در جهت نزولی (سطح {zz['pivot_price']:.2f}، {zz['bars_ago']} کندل قبل)"
            )

    # ===== اندیکاتورهای تکمیلی =====
    indicator_buy_score = 0
    indicator_buy_reasons = []
    indicator_sell_score = 0
    indicator_sell_reasons = []

    if current_rsi < 30:
        indicator_buy_score += 25
        indicator_buy_reasons.append(f"RSI در ناحیه‌ی اشباع فروش (مقدار {current_rsi:.1f})")
    elif current_rsi > 70:
        indicator_sell_score += 25
        indicator_sell_reasons.append(f"RSI در ناحیه‌ی اشباع خرید (مقدار {current_rsi:.1f})")
    elif current_rsi < 40:
        indicator_buy_score += 10
        indicator_buy_reasons.append(f"RSI نزدیک به ناحیه‌ی اشباع فروش (مقدار {current_rsi:.1f})")
    elif current_rsi > 60:
        indicator_sell_score += 10
        indicator_sell_reasons.append(f"RSI نزدیک به ناحیه‌ی اشباع خرید (مقدار {current_rsi:.1f})")

    if current_macd > current_macd_signal:
        indicator_buy_score += 20
        indicator_buy_reasons.append("همگرایی مثبت MACD نسبت به خط سیگنال")
    else:
        indicator_sell_score += 20
        indicator_sell_reasons.append("واگرایی منفی MACD نسبت به خط سیگنال")

    if current > current_ema21:
        indicator_buy_score += 15
        indicator_buy_reasons.append("قیمت بالاتر از میانگین متحرک نمایی ۲۱ (EMA 21)")
    else:
        indicator_sell_score += 15
        indicator_sell_reasons.append("قیمت پایین‌تر از میانگین متحرک نمایی ۲۱ (EMA 21)")

    if current > current_ema50:
        indicator_buy_score += 10
        indicator_buy_reasons.append("قیمت بالاتر از میانگین متحرک نمایی ۵۰ (EMA 50)")
    else:
        indicator_sell_score += 10
        indicator_sell_reasons.append("قیمت پایین‌تر از میانگین متحرک نمایی ۵۰ (EMA 50)")

    if current <= current_bb_low:
        indicator_buy_score += 15
        indicator_buy_reasons.append("برخورد قیمت با باند پایین بولینگر")
    elif current >= current_bb_high:
        indicator_sell_score += 15
        indicator_sell_reasons.append("برخورد قیمت با باند بالای بولینگر")

    if current > current_vwap:
        indicator_buy_score += 10
        indicator_buy_reasons.append("قیمت بالاتر از میانگین وزنی حجمی (VWAP)")
    else:
        indicator_sell_score += 10
        indicator_sell_reasons.append("قیمت پایین‌تر از میانگین وزنی حجمی (VWAP)")

    # ===== جمع‌بندی نهایی =====
    total_buy_score = ict_buy_score + indicator_buy_score
    total_sell_score = ict_sell_score + indicator_sell_score
    total_buy_reasons = ict_buy_reasons + indicator_buy_reasons
    total_sell_reasons = ict_sell_reasons + indicator_sell_reasons

    direction = None
    reasons = []
    score = 0
    strength = "NORMAL"

    if total_buy_score >= total_sell_score:
        direction_candidate = "BUY"
        score = total_buy_score
        reasons_candidate = total_buy_reasons
    else:
        direction_candidate = "SELL"
        score = total_sell_score
        reasons_candidate = total_sell_reasons

    if score >= MIN_SCORE_NORMAL:
        direction = direction_candidate
        reasons = reasons_candidate
        strength = "NORMAL"
    elif score >= MIN_SCORE_WEAK:
        direction = direction_candidate
        reasons = reasons_candidate
        strength = "WEAK"
    else:
        # امتیاز خیلی پایینه - هیچ ستاپ معتبری نیست، سکوت صادقانه
        return None, None

    # ===== محاسبه Entry/SL/TP =====
    from database import get_setting
    rr_ratio = float(get_setting('rr_ratio') or '2')
    RISK = 5.0
    REWARD = RISK * rr_ratio

    if direction == "BUY":
        entry = round(current, 2)
        sl = round(current - RISK, 2)
        tp = round(current + REWARD, 2)
    else:
        entry = round(current, 2)
        sl = round(current + RISK, 2)
        tp = round(current - REWARD, 2)

    signal = {
        'direction': direction,
        'entry': entry,
        'sl': sl,
        'tp': tp,
        'strength': strength,
    }

    if strength == "WEAK":
        reasons = ["⚠️ سیگنال ضعیف - ستاپ کامل ICT شکل نگرفته، این ترکیب امتیاز پایینی دارد"] + reasons

    if not is_real:
        reasons = ["⚠️ هشدار: این تحلیل روی داده‌ی تستی/شبیه‌سازی‌شده انجام شده، نه قیمت واقعی بازار"] + reasons

    analysis = {
        'reasons': reasons,
        'style': 'ICT',
        'score': score,
        'strength': strength,
    }

    return signal, analysis
