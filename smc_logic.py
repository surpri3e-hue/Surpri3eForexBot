import numpy as np
import pandas as pd
from ta import add_all_ta_features
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands
from ta.volume import VolumeWeightedAveragePrice

def analyze_smc(df):
    """
    تحلیل SMC + اندیکاتورهای حرفه‌ای
    اگر SMC سیگنال نداد، اندیکاتورها سیگنال میدن
    """
    if df is None or len(df) < 30:
        return None, None

    # ===== اضافه کردن اندیکاتورها با ta =====
    df_copy = df.copy()
    
    # RSI
    rsi = RSIIndicator(close=df_copy['Close'], window=14)
    df_copy['rsi'] = rsi.rsi()
    
    # MACD
    macd = MACD(close=df_copy['Close'])
    df_copy['macd'] = macd.macd()
    df_copy['macd_signal'] = macd.macd_signal()
    
    # EMA
    df_copy['ema21'] = EMAIndicator(close=df_copy['Close'], window=21).ema_indicator()
    df_copy['ema50'] = EMAIndicator(close=df_copy['Close'], window=50).ema_indicator()
    
    # بولینگر باند
    bb = BollingerBands(close=df_copy['Close'], window=20, window_dev=2)
    df_copy['bb_low'] = bb.bollinger_lband()
    df_copy['bb_high'] = bb.bollinger_hband()
    
    # VWAP
    vwap = VolumeWeightedAveragePrice(
        high=df_copy['High'],
        low=df_copy['Low'],
        close=df_copy['Close'],
        volume=df_copy['Volume']
    )
    df_copy['vwap'] = vwap.volume_weighted_average_price()

    # ===== گرفتن مقادیر لحظه‌ای =====
    current = df_copy['Close'].iloc[-1]
    prev = df_copy['Close'].iloc[-2]
    
    current_rsi = df_copy['rsi'].iloc[-1]
    current_macd = df_copy['macd'].iloc[-1]
    current_macd_signal = df_copy['macd_signal'].iloc[-1]
    current_ema21 = df_copy['ema21'].iloc[-1]
    current_ema50 = df_copy['ema50'].iloc[-1]
    current_bb_low = df_copy['bb_low'].iloc[-1]
    current_bb_high = df_copy['bb_high'].iloc[-1]
    current_vwap = df_copy['vwap'].iloc[-1]

    # ===== 1. تحلیل SMC =====
    smc_buy_score = 0
    smc_buy_reasons = []
    smc_sell_score = 0
    smc_sell_reasons = []

    # ===== SMC: Order Block =====
    close = df_copy['Close'].values
    high = df_copy['High'].values
    low = df_copy['Low'].values
    open_price = df_copy['Open'].values

    buy_ob = None
    sell_ob = None

    if len(df) >= 20:
        avg_volume = np.mean(df['Volume'].values[-20:])
        
        for i in range(len(df)-3, 0, -1):
            if close[i] < open_price[i]:
                if df['Volume'].values[i] > avg_volume * 1.5:
                    if close[i+1] > high[i]:
                        buy_ob = {'price': high[i]}
                        break
        
        for i in range(len(df)-3, 0, -1):
            if close[i] > open_price[i]:
                if df['Volume'].values[i] > avg_volume * 1.5:
                    if close[i+1] < low[i]:
                        sell_ob = {'price': low[i]}
                        break

    if buy_ob:
        smc_buy_score += 35
        smc_buy_reasons.append("Order Block خرید")
    if sell_ob:
        smc_sell_score += 35
        smc_sell_reasons.append("Order Block فروش")

    # ===== SMC: FVG =====
    fvg_up = None
    fvg_down = None

    if len(df) >= 5:
        for i in range(len(df)-3, 0, -1):
            if low[i] > high[i+1] and high[i-1] < low[i]:
                fvg_up = {'upper': low[i], 'lower': high[i+1]}
                break
            if high[i] < low[i+1] and low[i-1] > high[i]:
                fvg_down = {'upper': low[i+1], 'lower': high[i]}
                break

    if fvg_up:
        smc_buy_score += 25
        smc_buy_reasons.append("FVG صعودی")
    if fvg_down:
        smc_sell_score += 25
        smc_sell_reasons.append("FVG نزولی")

    # ===== SMC: Liquidity Sweep =====
    buy_sweep = False
    sell_sweep = False

    if len(high) >= 30:
        highest = max(high[-30:])
        lowest = min(low[-30:])
        
        if high[-1] > highest - 1 and current < highest - 3:
            buy_sweep = True
        if low[-1] < lowest + 1 and current > lowest + 3:
            sell_sweep = True

    if sell_sweep:
        smc_buy_score += 20
        smc_buy_reasons.append("شکار نقدینگی فروش")
    if buy_sweep:
        smc_sell_score += 20
        smc_sell_reasons.append("شکار نقدینگی خرید")

    # ===== SMC: MSS =====
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
        smc_buy_score += 20
        smc_buy_reasons.append("تغییر ساختار صعودی (MSS)")
    if mss_down:
        smc_sell_score += 20
        smc_sell_reasons.append("تغییر ساختار نزولی (MSS)")

    # ===== SMC: BOS =====
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
        smc_buy_score += 15
        smc_buy_reasons.append("شکست سقف قبلی (BOS)")
    if bos_down:
        smc_sell_score += 15
        smc_sell_reasons.append("شکست کف قبلی (BOS)")

    # ===== 2. اندیکاتورها (برای زمانی که SMC سیگنال نداد) =====
    indicator_buy_score = 0
    indicator_buy_reasons = []
    indicator_sell_score = 0
    indicator_sell_reasons = []

    # ===== RSI =====
    if current_rsi < 30:
        indicator_buy_score += 25
        indicator_buy_reasons.append(f"RSI اشباع فروش ({current_rsi:.1f})")
    elif current_rsi > 70:
        indicator_sell_score += 25
        indicator_sell_reasons.append(f"RSI اشباع خرید ({current_rsi:.1f})")
    elif current_rsi < 40:
        indicator_buy_score += 10
        indicator_buy_reasons.append(f"RSI نزدیک اشباع فروش ({current_rsi:.1f})")
    elif current_rsi > 60:
        indicator_sell_score += 10
        indicator_sell_reasons.append(f"RSI نزدیک اشباع خرید ({current_rsi:.1f})")

    # ===== MACD =====
    if current_macd > current_macd_signal:
        indicator_buy_score += 20
        indicator_buy_reasons.append("MACD صعودی")
    else:
        indicator_sell_score += 20
        indicator_sell_reasons.append("MACD نزولی")

    # ===== EMA =====
    if current > current_ema21:
        indicator_buy_score += 15
        indicator_buy_reasons.append("قیمت بالای EMA 21")
    else:
        indicator_sell_score += 15
        indicator_sell_reasons.append("قیمت پایین‌تر از EMA 21")

    if current > current_ema50:
        indicator_buy_score += 10
        indicator_buy_reasons.append("قیمت بالای EMA 50")
    else:
        indicator_sell_score += 10
        indicator_sell_reasons.append("قیمت پایین‌تر از EMA 50")

    # ===== بولینگر =====
    if current <= current_bb_low:
        indicator_buy_score += 15
        indicator_buy_reasons.append("برخورد به باند پایین بولینگر")
    elif current >= current_bb_high:
        indicator_sell_score += 15
        indicator_sell_reasons.append("برخورد به باند بالای بولینگر")

    # ===== VWAP =====
    if current > current_vwap:
        indicator_buy_score += 10
        indicator_buy_reasons.append("قیمت بالای VWAP")
    else:
        indicator_sell_score += 10
        indicator_sell_reasons.append("قیمت پایین‌تر از VWAP")

    # ===== 3. انتخاب نهایی (ترکیب SMC + اندیکاتورها) =====
    total_buy_score = smc_buy_score + indicator_buy_score
    total_sell_score = smc_sell_score + indicator_sell_score
    total_buy_reasons = smc_buy_reasons + indicator_buy_reasons
    total_sell_reasons = smc_sell_reasons + indicator_sell_reasons

    direction = None
    reasons = []

    if total_buy_score >= 30 and total_buy_score > total_sell_score:
        direction = "BUY"
        reasons = total_buy_reasons
    elif total_sell_score >= 30 and total_sell_score > total_buy_score:
        direction = "SELL"
        reasons = total_sell_reasons
    else:
        # ===== آخرین راهکار: تغییر قیمت (فقط در صورت عدم وجود هیچ سیگنالی) =====
        price_change = ((current - prev) / prev) * 100
        if price_change > 0.1:
            direction = "BUY"
            reasons = [f"افزایش قیمت لحظه‌ای ({price_change:.2f}%)"]
        elif price_change < -0.1:
            direction = "SELL"
            reasons = [f"کاهش قیمت لحظه‌ای ({price_change:.2f}%)"]
        else:
            return None, None

    # ===== 4. محاسبه Entry/SL/TP =====
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
    }

    analysis = {
        'reasons': reasons,
        'style': 'SMC'
    }

    return signal, analysis
