import numpy as np

def analyze_smc(df):
    """
    تحلیل Smart Money با خروجی تضمینی
    """
    if df is None or len(df) < 20:
        return None, None

    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values

    current = close[-1]
    prev = close[-2]

    # ===== Order Block =====
    buy_ob = None
    sell_ob = None

    if len(df) >= 15:
        for i in range(len(df)-3, 0, -1):
            if df['Close'].iloc[i] < df['Open'].iloc[i]:
                if i > 5 and df['Volume'].iloc[i] > np.mean(df['Volume'].iloc[i-5:i]) * 1.5:
                    if df['Close'].iloc[i+1] > df['High'].iloc[i]:
                        buy_ob = {'price': df['High'].iloc[i]}
                        break

        for i in range(len(df)-3, 0, -1):
            if df['Close'].iloc[i] > df['Open'].iloc[i]:
                if i > 5 and df['Volume'].iloc[i] > np.mean(df['Volume'].iloc[i-5:i]) * 1.5:
                    if df['Close'].iloc[i+1] < df['Low'].iloc[i]:
                        sell_ob = {'price': df['Low'].iloc[i]}
                        break

    # ===== FVG =====
    fvg_up = None
    fvg_down = None

    if len(df) >= 5:
        for i in range(len(df)-3, 0, -1):
            if df['Low'].iloc[i] > df['High'].iloc[i+1] and df['High'].iloc[i-1] < df['Low'].iloc[i]:
                if current < df['Low'].iloc[i] and current > df['High'].iloc[i+1]:
                    fvg_up = {'upper': df['Low'].iloc[i], 'lower': df['High'].iloc[i+1]}
                    break

            if df['High'].iloc[i] < df['Low'].iloc[i+1] and df['Low'].iloc[i-1] > df['High'].iloc[i]:
                if current > df['High'].iloc[i] and current < df['Low'].iloc[i+1]:
                    fvg_down = {'upper': df['Low'].iloc[i+1], 'lower': df['High'].iloc[i]}
                    break

    # ===== Liquidity Sweep =====
    buy_sweep = False
    sell_sweep = False

    if len(high) > 30:
        highest = max(high[-30:])
        if current < highest - 5 and high[-1] > highest - 2:
            buy_sweep = True

        lowest = min(low[-30:])
        if current > lowest + 5 and low[-1] < lowest + 2:
            sell_sweep = True

    # ===== Market Structure Shift =====
    mss_up = False
    mss_down = False

    if len(high) > 15:
        last_high = max(high[-5:])
        last_low = min(low[-5:])

        if current > last_high and low[-1] > min(low[-10:-5]):
            mss_up = True

        if current < last_low and high[-1] < max(high[-10:-5]):
            mss_down = True

    # ===== امتیاز BUY =====
    buy_score = 0
    buy_reasons = []

    if buy_ob:
        buy_score += 35
        buy_reasons.append(f"Order Block خرید در {buy_ob['price']:.2f}")
    if fvg_up:
        buy_score += 25
        buy_reasons.append(f"FVG صعودی ({fvg_up['lower']:.2f} - {fvg_up['upper']:.2f})")
    if sell_sweep:
        buy_score += 20
        buy_reasons.append("شکار نقدینگی فروش")
    if mss_up:
        buy_score += 20
        buy_reasons.append("تغییر ساختار صعودی")

    # ===== امتیاز SELL =====
    sell_score = 0
    sell_reasons = []

    if sell_ob:
        sell_score += 35
        sell_reasons.append(f"Order Block فروش در {sell_ob['price']:.2f}")
    if fvg_down:
        sell_score += 25
        sell_reasons.append(f"FVG نزولی ({fvg_down['upper']:.2f} - {fvg_down['lower']:.2f})")
    if buy_sweep:
        sell_score += 20
        sell_reasons.append("شکار نقدینگی خرید")
    if mss_down:
        sell_score += 20
        sell_reasons.append("تغییر ساختار نزولی")

    # ===== انتخاب نهایی =====
    direction = None
    reasons = []

    if buy_score >= 25 and buy_score > sell_score:
        direction = "BUY"
        reasons = buy_reasons
    elif sell_score >= 25 and sell_score > buy_score:
        direction = "SELL"
        reasons = sell_reasons
    else:
        # ===== سیگنال اضطراری بر اساس تغییر قیمت =====
        price_change = ((current - prev) / prev) * 100
        
        if price_change > 0.05:
            direction = "BUY"
            reasons = [f"افزایش قیمت لحظه‌ای ({price_change:.2f}%)"]
        elif price_change < -0.05:
            direction = "SELL"
            reasons = [f"کاهش قیمت لحظه‌ای ({price_change:.2f}%)"]
        else:
            # ===== آخرین راهکار: RSI =====
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
                
                if rsi < 40:
                    direction = "BUY"
                    reasons = [f"RSI در منطقه اشباع فروش ({rsi:.1f})"]
                elif rsi > 60:
                    direction = "SELL"
                    reasons = [f"RSI در منطقه اشباع خرید ({rsi:.1f})"]
                else:
                    # ===== اگر هیچی نشد، BUY پیش‌فرض (با احتیاط) =====
                    direction = "BUY"
                    reasons = ["شرایط خنثی - BUY پیش‌فرض (با احتیاط)"]
                    
            except:
                # ===== اگر RSI ارور داد، BUY پیش‌فرض =====
                direction = "BUY"
                reasons = ["خطا در محاسبه RSI - BUY پیش‌فرض (با احتیاط)"]

    # ===== Entry/SL/TP =====
    from database import get_setting
    rr_ratio = float(get_setting('rr_ratio') or '2')
    RISK = 5.0
    REWARD = RISK * rr_ratio

    if direction == "BUY":
        if buy_ob:
            entry = round(buy_ob['price'] + 0.5, 2)
        else:
            entry = round(current, 2)
        sl = round(entry - RISK, 2)
        tp = round(entry + REWARD, 2)
    else:
        if sell_ob:
            entry = round(sell_ob['price'] - 0.5, 2)
        else:
            entry = round(current, 2)
        sl = round(entry + RISK, 2)
        tp = round(entry - REWARD, 2)

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
