import numpy as np

def analyze_smc(df):
    """
    تحلیل SMC واقعی - فقط Price Action
    اگر هیچ شرایطی برقرار نبود، None برمیگردونه
    """
    if df is None or len(df) < 30:
        return None, None

    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    open_price = df['Open'].values

    current = close[-1]
    prev = close[-2]

    # ===== 1. Order Block (با حجم) =====
    buy_ob = None
    sell_ob = None

    if len(df) >= 20:
        avg_volume = np.mean(df['Volume'].values[-20:])
        
        for i in range(len(df)-3, 0, -1):
            if close[i] < open_price[i]:
                if df['Volume'].values[i] > avg_volume * 1.5:
                    if close[i+1] > high[i]:
                        buy_ob = {'price': high[i], 'volume': df['Volume'].values[i]}
                        break
        
        for i in range(len(df)-3, 0, -1):
            if close[i] > open_price[i]:
                if df['Volume'].values[i] > avg_volume * 1.5:
                    if close[i+1] < low[i]:
                        sell_ob = {'price': low[i], 'volume': df['Volume'].values[i]}
                        break

    # ===== 2. FVG =====
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

    # ===== 3. Liquidity Sweep =====
    buy_sweep = False
    sell_sweep = False

    if len(high) >= 30:
        highest = max(high[-30:])
        lowest = min(low[-30:])
        
        if high[-1] > highest - 1 and current < highest - 3:
            buy_sweep = True
        if low[-1] < lowest + 1 and current > lowest + 3:
            sell_sweep = True

    # ===== 4. Market Structure Shift =====
    mss_up = False
    mss_down = False

    if len(high) >= 15:
        prev_high = max(high[-15:-5])
        prev_low = min(low[-15:-5])
        
        if current > prev_high and low[-1] > prev_low:
            mss_up = True
        if current < prev_low and high[-1] < prev_high:
            mss_down = True

    # ===== 5. Break of Structure =====
    bos_up = False
    bos_down = False

    if len(high) >= 10:
        last_high = max(high[-6:-1])
        last_low = min(low[-6:-1])
        
        if current > last_high and high[-1] > last_high:
            bos_up = True
        if current < last_low and low[-1] < last_low:
            bos_down = True

    # ===== 6. امتیازدهی SMC =====
    buy_score = 0
    buy_reasons = []
    sell_score = 0
    sell_reasons = []

    if buy_ob:
        buy_score += 35
        buy_reasons.append(f"Order Block خرید در {buy_ob['price']:.2f} (حجم: {buy_ob['volume']})")
    if fvg_up:
        buy_score += 25
        buy_reasons.append("FVG صعودی")
    if sell_sweep:
        buy_score += 20
        buy_reasons.append("شکار نقدینگی فروش")
    if mss_up:
        buy_score += 20
        buy_reasons.append("تغییر ساختار صعودی (MSS)")
    if bos_up:
        buy_score += 15
        buy_reasons.append("شکست سقف قبلی (BOS)")

    if sell_ob:
        sell_score += 35
        sell_reasons.append(f"Order Block فروش در {sell_ob['price']:.2f} (حجم: {sell_ob['volume']})")
    if fvg_down:
        sell_score += 25
        sell_reasons.append("FVG نزولی")
    if buy_sweep:
        sell_score += 20
        sell_reasons.append("شکار نقدینگی خرید")
    if mss_down:
        sell_score += 20
        sell_reasons.append("تغییر ساختار نزولی (MSS)")
    if bos_down:
        sell_score += 15
        sell_reasons.append("شکست کف قبلی (BOS)")

    # ===== 7. انتخاب نهایی =====
    direction = None
    reasons = []

    if buy_score >= 35 and buy_score > sell_score:
        direction = "BUY"
        reasons = buy_reasons
    elif sell_score >= 35 and sell_score > buy_score:
        direction = "SELL"
        reasons = sell_reasons
    else:
        # ===== هیچ سیگنالی پیدا نشد =====
        return None, None

    # ===== 8. محاسبه Entry/SL/TP =====
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
