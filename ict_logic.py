import numpy as np

def analyze_ict(df):
    """
    تحلیل ICT واقعی - فقط ساختار بازار و Price Action
    """
    if df is None or len(df) < 30:
        return None, None

    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    open_price = df['Open'].values

    current = close[-1]
    prev = close[-2]

    # ===== 1. شناسایی ساختار بازار (Market Structure) =====
    # ===== 1.1 شکست ساختار (BOS - Break of Structure) =====
    bos_up = False
    bos_down = False

    # آخرین سقف و کف مشخص
    if len(high) >= 10:
        last_high = max(high[-6:-1])
        last_low = min(low[-6:-1])
        
        # شکست سقف قبلی (BOS UP)
        if current > last_high and high[-1] > last_high:
            bos_up = True
        
        # شکست کف قبلی (BOS DOWN)
        if current < last_low and low[-1] < last_low:
            bos_down = True

    # ===== 1.2 تغییر ساختار بازار (MSS - Market Structure Shift) =====
    mss_up = False
    mss_down = False

    if len(high) >= 15:
        # سقف و کف قبلی
        prev_high = max(high[-15:-5])
        prev_low = min(low[-15:-5])
        
        # تغییر ساختار صعودی: شکست سقف قبلی با برگشت
        if current > prev_high and low[-1] > prev_low:
            mss_up = True
        
        # تغییر ساختار نزولی: شکست کف قبلی با برگشت
        if current < prev_low and high[-1] < prev_high:
            mss_down = True

    # ===== 2. شناسایی FVG (Fair Value Gap) =====
    fvg_up = None
    fvg_down = None

    if len(df) >= 5:
        for i in range(len(df)-3, 0, -1):
            # FVG صعودی: کندل i پایین‌تر از کندل i+1 و کندل i-1 بالاتر از کندل i
            if low[i] > high[i+1] and high[i-1] < low[i]:
                fvg_up = {
                    'upper': low[i],
                    'lower': high[i+1],
                    'level': (low[i] + high[i+1]) / 2
                }
                break
            
            # FVG نزولی: کندل i بالاتر از کندل i+1 و کندل i-1 پایین‌تر از کندل i
            if high[i] < low[i+1] and low[i-1] > high[i]:
                fvg_down = {
                    'upper': low[i+1],
                    'lower': high[i],
                    'level': (low[i+1] + high[i]) / 2
                }
                break

    # ===== 3. شناسایی Order Block =====
    buy_ob = None
    sell_ob = None

    if len(df) >= 15:
        for i in range(len(df)-3, 0, -1):
            # Order Block خرید: کندل نزولی با حجم بالا که بعدش قیمت بالا رفت
            if close[i] < open_price[i]:
                if close[i+1] > high[i]:
                    buy_ob = {
                        'price': high[i],
                        'low': low[i],
                        'high': high[i]
                    }
                    break
        
        for i in range(len(df)-3, 0, -1):
            # Order Block فروش: کندل صعودی با حجم بالا که بعدش قیمت پایین رفت
            if close[i] > open_price[i]:
                if close[i+1] < low[i]:
                    sell_ob = {
                        'price': low[i],
                        'low': low[i],
                        'high': high[i]
                    }
                    break

    # ===== 4. شناسایی نقدینگی (Liquidity) =====
    buy_liquidity = False
    sell_liquidity = False
    liquidity_high = None
    liquidity_low = None

    if len(high) >= 30:
        # نقدینگی خرید: قیمت به بالاترین حد چند روزه رسیده
        recent_highs = high[-30:]
        if current > max(recent_highs) - 2:
            buy_liquidity = True
            liquidity_high = max(recent_highs)
        
        # نقدینگی فروش: قیمت به پایین‌ترین حد چند روزه رسیده
        recent_lows = low[-30:]
        if current < min(recent_lows) + 2:
            sell_liquidity = True
            liquidity_low = min(recent_lows)

    # ===== 5. شکار نقدینگی (Liquidity Sweep) =====
    buy_sweep = False
    sell_sweep = False

    if len(high) >= 30:
        highest = max(high[-30:])
        lowest = min(low[-30:])
        
        # شکار نقدینگی خرید: قیمت به بالاترین حد رسیده و برگشته
        if high[-1] > highest - 1 and current < highest - 3:
            buy_sweep = True
        
        # شکار نقدینگی فروش: قیمت به پایین‌ترین حد رسیده و برگشته
        if low[-1] < lowest + 1 and current > lowest + 3:
            sell_sweep = True

    # ===== 6. Decision Making =====
    buy_score = 0
    buy_reasons = []
    sell_score = 0
    sell_reasons = []

    # ===== شرایط BUY =====
    if bos_up:
        buy_score += 30
        buy_reasons.append("شکست سقف قبلی (BOS UP)")
    
    if mss_up:
        buy_score += 25
        buy_reasons.append("تغییر ساختار صعودی (MSS UP)")
    
    if fvg_up:
        buy_score += 20
        buy_reasons.append(f"FVG صعودی در محدوده {fvg_up['lower']:.2f} - {fvg_up['upper']:.2f}")
    
    if buy_ob:
        buy_score += 25
        buy_reasons.append(f"Order Block خرید در {buy_ob['price']:.2f}")
    
    if buy_liquidity:
        buy_score += 15
        buy_reasons.append(f"نقدینگی خرید در {liquidity_high:.2f}")
    
    if sell_sweep:
        buy_score += 20
        buy_reasons.append("شکار نقدینگی فروش")

    # ===== شرایط SELL =====
    if bos_down:
        sell_score += 30
        sell_reasons.append("شکست کف قبلی (BOS DOWN)")
    
    if mss_down:
        sell_score += 25
        sell_reasons.append("تغییر ساختار نزولی (MSS DOWN)")
    
    if fvg_down:
        sell_score += 20
        sell_reasons.append(f"FVG نزولی در محدوده {fvg_down['lower']:.2f} - {fvg_down['upper']:.2f}")
    
    if sell_ob:
        sell_score += 25
        sell_reasons.append(f"Order Block فروش در {sell_ob['price']:.2f}")
    
    if sell_liquidity:
        sell_score += 15
        sell_reasons.append(f"نقدینگی فروش در {liquidity_low:.2f}")
    
    if buy_sweep:
        sell_score += 20
        sell_reasons.append("شکار نقدینگی خرید")

    # ===== انتخاب نهایی =====
    direction = None
    reasons = []

    if buy_score >= 40 and buy_score > sell_score:
        direction = "BUY"
        reasons = buy_reasons
    elif sell_score >= 40 and sell_score > buy_score:
        direction = "SELL"
        reasons = sell_reasons
    else:
        # ===== اگر هیچ شرایطی برقرار نبود =====
        # بررسی تغییر قیمت ساده
        price_change = ((current - prev) / prev) * 100
        if price_change > 0.2:
            direction = "BUY"
            reasons = [f"افزایش قیمت لحظه‌ای ({price_change:.2f}%)"]
        elif price_change < -0.2:
            direction = "SELL"
            reasons = [f"کاهش قیمت لحظه‌ای ({price_change:.2f}%)"]
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
    }

    analysis = {
        'reasons': reasons,
        'style': 'ICT'
    }

    return signal, analysis
