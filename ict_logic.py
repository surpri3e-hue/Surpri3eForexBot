import numpy as np

def analyze_ict(df):
    """
    تحلیل ICT
    """
    if df is None or len(df) < 20:
        return None, None

    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values

    current = close[-1]
    prev = close[-2]

    # ===== ساختار بازار =====
    bos_up = False
    bos_down = False

    last_high = max(high[-5:])
    last_low = min(low[-5:])

    if current > last_high and len(high) > 10:
        if current > max(high[-10:-5]) + 2:
            bos_up = True

    if current < last_low and len(low) > 10:
        if current < min(low[-10:-5]) - 2:
            bos_down = True

    # ===== FVG =====
    fvg_up = False
    fvg_down = False

    if len(df) >= 4:
        for i in range(len(df)-3, 0, -1):
            if df['Low'].iloc[i] > df['High'].iloc[i+1] and df['High'].iloc[i-1] < df['Low'].iloc[i]:
                if current < df['Low'].iloc[i] and current > df['High'].iloc[i+1]:
                    fvg_up = True
                    break

            if df['High'].iloc[i] < df['Low'].iloc[i+1] and df['Low'].iloc[i-1] > df['High'].iloc[i]:
                if current > df['High'].iloc[i] and current < df['Low'].iloc[i+1]:
                    fvg_down = True
                    break

    # ===== Order Block =====
    buy_ob = False
    sell_ob = False

    if len(df) >= 10:
        for i in range(len(df)-2, 0, -1):
            if df['Close'].iloc[i] < df['Open'].iloc[i]:
                if df['Close'].iloc[i+1] > df['Open'].iloc[i+1]:
                    if current > df['High'].iloc[i]:
                        buy_ob = True
                        break

        for i in range(len(df)-2, 0, -1):
            if df['Close'].iloc[i] > df['Open'].iloc[i]:
                if df['Close'].iloc[i+1] < df['Open'].iloc[i+1]:
                    if current < df['Low'].iloc[i]:
                        sell_ob = True
                        break

    # ===== نقدینگی =====
    buy_liquidity = False
    sell_liquidity = False

    if len(high) > 20:
        recent_highs = high[-20:]
        if current > max(recent_highs) - 2:
            buy_liquidity = True

        recent_lows = low[-20:]
        if current < min(recent_lows) + 2:
            sell_liquidity = True

    # ===== میانگین متحرک =====
    ma20 = np.mean(close[-20:])
    ma50 = np.mean(close[-50:]) if len(close) >= 50 else ma20

    # ===== امتیاز BUY =====
    buy_score = 0
    buy_reasons = []

    if bos_up:
        buy_score += 30
        buy_reasons.append("شکست سقف قبلی (BOS UP)")
    if fvg_up:
        buy_score += 25
        buy_reasons.append("FVG صعودی")
    if buy_ob:
        buy_score += 25
        buy_reasons.append("Order Block خرید")
    if buy_liquidity:
        buy_score += 15
        buy_reasons.append("نقدینگی خرید")
    if current > ma20:
        buy_score += 15
        buy_reasons.append("قیمت بالای MA20")
    if current > ma50:
        buy_score += 10
        buy_reasons.append("قیمت بالای MA50")

    # ===== امتیاز SELL =====
    sell_score = 0
    sell_reasons = []

    if bos_down:
        sell_score += 30
        sell_reasons.append("شکست کف قبلی (BOS DOWN)")
    if fvg_down:
        sell_score += 25
        sell_reasons.append("FVG نزولی")
    if sell_ob:
        sell_score += 25
        sell_reasons.append("Order Block فروش")
    if sell_liquidity:
        sell_score += 15
        sell_reasons.append("نقدینگی فروش")
    if current < ma20:
        sell_score += 15
        sell_reasons.append("قیمت پایین‌تر از MA20")
    if current < ma50:
        sell_score += 10
        sell_reasons.append("قیمت پایین‌تر از MA50")

    # ===== انتخاب نهایی =====
    direction = None
    reasons = []

    if buy_score >= 30 and buy_score > sell_score:
        direction = "BUY"
        reasons = buy_reasons
    elif sell_score >= 30 and sell_score > buy_score:
        direction = "SELL"
        reasons = sell_reasons
    else:
        price_change = ((current - prev) / prev) * 100
        
        if price_change > 0.1:
            direction = "BUY"
            reasons = ["افزایش قیمت لحظه‌ای"]
        elif price_change < -0.1:
            direction = "SELL"
            reasons = ["کاهش قیمت لحظه‌ای"]
        else:
            try:
                delta = np.diff(close)
                gain = np.where(delta > 0, delta, 0)
                loss = np.where(delta < 0, -delta, 0)
                avg_gain = np.mean(gain[-14:])
                avg_loss = np.mean(loss[-14:])
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                
                if rsi < 30:
                    direction = "BUY"
                    reasons = [f"RSI در منطقه اشباع فروش ({rsi:.1f})"]
                elif rsi > 70:
                    direction = "SELL"
                    reasons = [f"RSI در منطقه اشباع خرید ({rsi:.1f})"]
                else:
                    return None, None
                    
            except:
                return None, None

    # ===== Entry/SL/TP =====
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
        'style': 'ICT'
    }

    return signal, analysis
