# ict_logic.py
import numpy as np

def analyze_ict(df):
    """
    تحلیل ICT حرفه‌ای با بررسی کامل ساختار بازار
    """
    if df is None or len(df) < 20:
        return None, None
    
    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    
    current = close[-1]
    
    # ===== 1. شناسایی ساختار بازار (Market Structure) =====
    bos_up = False
    bos_down = False
    
    # آخرین سقف و کف
    last_high = max(high[-5:])
    last_low = min(low[-5:])
    
    # شکست سقف قبلی (BOS UP)
    if current > last_high and len(high) > 10:
        if current > max(high[-10:-5]) + 2:
            bos_up = True
    
    # شکست کف قبلی (BOS DOWN)
    if current < last_low and len(low) > 10:
        if current < min(low[-10:-5]) - 2:
            bos_down = True
    
    # ===== 2. شناسایی FVG (Fair Value Gap) =====
    fvg_up = False
    fvg_down = False
    
    if len(df) >= 4:
        for i in range(len(df)-3, 0, -1):
            # FVG صعودی: کندل قبل بالا، کندل بعد پایین
            if df['Low'].iloc[i] > df['High'].iloc[i+1] and df['High'].iloc[i-1] < df['Low'].iloc[i]:
                if current < df['Low'].iloc[i] and current > df['High'].iloc[i+1]:
                    fvg_up = True
                    break
            
            # FVG نزولی: کندل قبل پایین، کندل بعد بالا
            if df['High'].iloc[i] < df['Low'].iloc[i+1] and df['Low'].iloc[i-1] > df['High'].iloc[i]:
                if current > df['High'].iloc[i] and current < df['Low'].iloc[i+1]:
                    fvg_down = True
                    break
    
    # ===== 3. شناسایی Order Block =====
    buy_ob = False
    sell_ob = False
    
    if len(df) >= 10:
        # آخرین کندل نزولی قبل از صعود
        for i in range(len(df)-2, 0, -1):
            if df['Close'].iloc[i] < df['Open'].iloc[i]:
                if df['Close'].iloc[i+1] > df['Open'].iloc[i+1]:
                    if current > df['High'].iloc[i]:
                        buy_ob = True
                        break
        
        # آخرین کندل صعودی قبل از نزول
        for i in range(len(df)-2, 0, -1):
            if df['Close'].iloc[i] > df['Open'].iloc[i]:
                if df['Close'].iloc[i+1] < df['Open'].iloc[i+1]:
                    if current < df['Low'].iloc[i]:
                        sell_ob = True
                        break
    
    # ===== 4. شناسایی نقدینگی (Liquidity) =====
    buy_liquidity = False
    sell_liquidity = False
    
    if len(high) > 20:
        # نقدینگی خرید (قیمت بالا)
        recent_highs = high[-20:]
        if current > max(recent_highs) - 2:
            buy_liquidity = True
        
        # نقدینگی فروش (قیمت پایین)
        recent_lows = low[-20:]
        if current < min(recent_lows) + 2:
            sell_liquidity = True
    
    # ===== 5. میانگین متحرک =====
    ma20 = np.mean(close[-20:])
    ma50 = np.mean(close[-50:]) if len(close) >= 50 else ma20
    
    # ===== 6. تصمیم نهایی =====
    reasons = []
    score = 0
    direction = None
    
    # شرایط BUY
    buy_score = 0
    if bos_up:
        buy_score += 30
        reasons.append("شکست سقف قبلی (BOS UP)")
    if fvg_up:
        buy_score += 25
        reasons.append("FVG صعودی شناسایی شد")
    if buy_ob:
        buy_score += 25
        reasons.append("Order Block خرید شناسایی شد")
    if buy_liquidity:
        buy_score += 15
        reasons.append("نقدینگی خرید شناسایی شد")
    if current > ma20:
        buy_score += 15
        reasons.append("قیمت بالای میانگین متحرک ۲۰")
    if current > ma50:
        buy_score += 10
        reasons.append("قیمت بالای میانگین متحرک ۵۰")
    
    # شرایط SELL
    sell_score = 0
    sell_reasons = []
    if bos_down:
        sell_score += 30
        sell_reasons.append("شکست کف قبلی (BOS DOWN)")
    if fvg_down:
        sell_score += 25
        sell_reasons.append("FVG نزولی شناسایی شد")
    if sell_ob:
        sell_score += 25
        sell_reasons.append("Order Block فروش شناسایی شد")
    if sell_liquidity:
        sell_score += 15
        sell_reasons.append("نقدینگی فروش شناسایی شد")
    if current < ma20:
        sell_score += 15
        sell_reasons.append("قیمت پایین‌تر از میانگین متحرک ۲۰")
    if current < ma50:
        sell_score += 10
        sell_reasons.append("قیمت پایین‌تر از میانگین متحرک ۵۰")
    
    # ===== 7. انتخاب جهت =====
    if buy_score >= 60 and buy_score > sell_score:
        direction = "BUY"
        score = buy_score
    elif sell_score >= 60 and sell_score > buy_score:
        direction = "SELL"
        score = sell_score
        reasons = sell_reasons
    else:
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
        'score': score
    }
    
    analysis = {
        'reasons': reasons,
        'score': score,
        'style': 'ICT'
    }
    
    return signal, analysis
