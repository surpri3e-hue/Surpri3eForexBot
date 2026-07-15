# ============================================================
# 📁 smc_logic.py
# 📌 وظیفه: تحلیل بازار با سبک SMC (Smart Money Concepts)
# 📅 بازنویسی: 2026-07-15
# ============================================================

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands
from ta.volume import VolumeWeightedAveragePrice

MIN_SCORE_WEAK = 15
MIN_SCORE_NORMAL = 30


def analyze_smc(df):
    """
    تحلیل SMC با تمرکز اصلی روی:
      - Order Block حجم‌محور (وزن بالا - امضای اصلی SMC)
      - Liquidity Sweep (شکار نقدینگی - وزن بالا)
      - FVG و MSS (وزن کمتر نسبت به ICT، چون در SMC نقش تکمیلی دارن)
    + اندیکاتورهای تکمیلی مشترک.

    قوانین سیگنال‌دهی مثل ict_logic:
        امتیاز >= 30  -> سیگنال عادی
        15 <= امتیاز < 30 -> سیگنال ضعیف (با برچسب هشدار)
        امتیاز < 15  -> هیچ سیگنالی (None, None)
    """
    if df is None or len(df) < 30:
        return None, None

    is_real = df.attrs.get('is_real_data', True)

    df_copy = df.copy()

    rsi = RSIIndicator(close=df_copy['Close'], window=14)
    df_copy['rsi'] = rsi.rsi()

    macd = MACD(close=df_copy['Close'])
    df_copy['macd'] = macd.macd()
    df_copy['macd_signal'] = macd.macd_signal()

    df_copy['ema21'] = EMAIndicator(close=df_copy['Close'], window=21).ema_indicator()
    df_copy['ema50'] = EMAIndicator(close=df_copy['Close'], window=50).ema_indicator()

    bb = BollingerBands(close=df_copy['Close'], window=20, window_dev=2)
    df_copy['bb_low'] = bb.bollinger_lband()
    df_copy['bb_high'] = bb.bollinger_hband()

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

    critical_values = [current_rsi, current_macd, current_macd_signal, current_ema21, current_ema50, current_vwap]
    if any(pd.isna(v) for v in critical_values):
        return None, None

    close = df_copy['Close'].values
    high = df_copy['High'].values
    low = df_copy['Low'].values
    open_price = df_copy['Open'].values
    volume = df_copy['Volume'].values

    smc_buy_score = 0
    smc_buy_reasons = []
    smc_sell_score = 0
    smc_sell_reasons = []

    # ===== Order Block حجم‌محور (وزن اصلی SMC = 35) =====
    buy_ob = None
    sell_ob = None
    if len(df) >= 20:
        avg_volume = np.mean(volume[-20:])
        for i in range(len(df) - 3, 0, -1):
            if close[i] < open_price[i] and volume[i] > avg_volume * 1.5 and close[i + 1] > high[i]:
                buy_ob = {'price': high[i]}
                break
        for i in range(len(df) - 3, 0, -1):
            if close[i] > open_price[i] and volume[i] > avg_volume * 1.5 and close[i + 1] < low[i]:
                sell_ob = {'price': low[i]}
                break

    if buy_ob:
        smc_buy_score += 35
        smc_buy_reasons.append("Order Block خرید با حجم بالا 🟢")
    if sell_ob:
        smc_sell_score += 35
        smc_sell_reasons.append("Order Block فروش با حجم بالا 🔴")

    # ===== Liquidity Sweep (وزن بالا = 25، امضای دوم SMC) =====
    buy_sweep = False
    sell_sweep = False
    if len(high) >= 30:
        highest = max(high[-30:-1])  # سقف ۲۹ کندل قبل، بدون کندل آخر
        lowest = min(low[-30:-1])

        # sweep فروش: کندل آخر سقف رو می‌زنه ولی close برمی‌گرده پایین‌تر (شکار خریداران دیرهنگام)
        if high[-1] > highest and close[-1] < highest:
            sell_sweep = True
        # sweep خرید: کندل آخر کف رو می‌زنه ولی close برمی‌گرده بالاتر (شکار فروشندگان دیرهنگام)
        if low[-1] < lowest and close[-1] > lowest:
            buy_sweep = True

    if buy_sweep:
        smc_buy_score += 25
        smc_buy_reasons.append("شکار نقدینگی کف قیمتی 💰")
    if sell_sweep:
        smc_sell_score += 25
        smc_sell_reasons.append("شکار نقدینگی سقف قیمتی 💰")

    # ===== FVG (وزن کمتر نسبت به ICT = 15) =====
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
        smc_buy_score += 15
        smc_buy_reasons.append("FVG صعودی 🎯")
    if fvg_down:
        smc_sell_score += 15
        smc_sell_reasons.append("FVG نزولی 🎯")

    # ===== MSS (وزن کمتر = 15) =====
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
        smc_buy_score += 15
        smc_buy_reasons.append("تغییر ساختار صعودی (MSS) 🔄")
    if mss_down:
        smc_sell_score += 15
        smc_sell_reasons.append("تغییر ساختار نزولی (MSS) 🔄")

    # ===== اندیکاتورهای تکمیلی (وزن کمتر نسبت به ICT چون SMC بیشتر ساختارمحوره) =====
    indicator_buy_score = 0
    indicator_buy_reasons = []
    indicator_sell_score = 0
    indicator_sell_reasons = []

    if current_rsi < 30:
        indicator_buy_score += 20
        indicator_buy_reasons.append(f"RSI اشباع فروش ({current_rsi:.1f}) 📉")
    elif current_rsi > 70:
        indicator_sell_score += 20
        indicator_sell_reasons.append(f"RSI اشباع خرید ({current_rsi:.1f}) 📈")
    elif current_rsi < 40:
        indicator_buy_score += 8
        indicator_buy_reasons.append(f"RSI نزدیک اشباع فروش ({current_rsi:.1f})")
    elif current_rsi > 60:
        indicator_sell_score += 8
        indicator_sell_reasons.append(f"RSI نزدیک اشباع خرید ({current_rsi:.1f})")

    if current_macd > current_macd_signal:
        indicator_buy_score += 15
        indicator_buy_reasons.append("MACD صعودی 📊")
    else:
        indicator_sell_score += 15
        indicator_sell_reasons.append("MACD نزولی 📊")

    if current > current_ema21:
        indicator_buy_score += 10
        indicator_buy_reasons.append("قیمت بالای EMA 21 📈")
    else:
        indicator_sell_score += 10
        indicator_sell_reasons.append("قیمت پایین‌تر از EMA 21 📉")

    if current > current_ema50:
        indicator_buy_score += 8
        indicator_buy_reasons.append("قیمت بالای EMA 50 📈")
    else:
        indicator_sell_score += 8
        indicator_sell_reasons.append("قیمت پایین‌تر از EMA 50 📉")

    if current <= current_bb_low:
        indicator_buy_score += 10
        indicator_buy_reasons.append("برخورد به باند پایین بولینگر ⬇️")
    elif current >= current_bb_high:
        indicator_sell_score += 10
        indicator_sell_reasons.append("برخورد به باند بالای بولینگر ⬆️")

    if current > current_vwap:
        indicator_buy_score += 8
        indicator_buy_reasons.append("قیمت بالای VWAP 💎")
    else:
        indicator_sell_score += 8
        indicator_sell_reasons.append("قیمت پایین‌تر از VWAP 💎")

    # ===== جمع‌بندی نهایی =====
    total_buy_score = smc_buy_score + indicator_buy_score
    total_sell_score = smc_sell_score + indicator_sell_score
    total_buy_reasons = smc_buy_reasons + indicator_buy_reasons
    total_sell_reasons = smc_sell_reasons + indicator_sell_reasons

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
        reasons = ["⚠️ سیگنال ضعیف - ستاپ کامل SMC شکل نگرفته، این ترکیب امتیاز پایینی دارد"] + reasons

    if not is_real:
        reasons = ["⚠️ هشدار: این تحلیل روی داده‌ی تستی/شبیه‌سازی‌شده انجام شده، نه قیمت واقعی بازار"] + reasons

    analysis = {
        'reasons': reasons,
        'style': 'SMC',
        'score': score,
        'strength': strength,
    }

    return signal, analysis
