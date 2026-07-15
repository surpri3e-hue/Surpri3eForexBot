# smc_logic.py
import numpy as np

def analyze_smc(df):
    """
    تحلیل Smart Money Concepts (SMC) حرفه‌ای
    """
    if df is None or len(df) < 20:
        return None, None
    
    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    
    current = close[-1]
    
    # ===== 1. شناسایی Order Block (سفارش بلوک) =====
    buy_ob = None
    sell_ob = None
    
    if len(df) >= 15:
        for i in range(len(df)-3, 0, -1):
            # Order Block خرید: کندل نزولی با حجم بالا که بعدش قیمت بالا رفت
            if df['Close'].iloc[i] < df['Open'].iloc[i]:
                # بررسی افزایش حجم
                if i > 5 and df['Volume'].iloc[i] > np.mean(df['Volume'].iloc[i-5:i]) * 1.5:
                    if df['Close'].iloc[i+1] > df['High'].iloc[i]:
                        buy_ob = {'price': df['High'].iloc[i], 'index': i}
                        break
        
        for i in range(len(df)-3, 0, -1):
            # Order Block فروش: کندل صعودی با حجم بالا که بعدش قیمت پایین رفت
            if df['Close'].iloc[i] > df['Open'].iloc[i]:
                if i > 5 and df['Volume'].iloc[i] > np.mean(df['Volume'].iloc[i-5:i]) * 1.5:
                    if df['Close'].iloc[i+1] < df['Low'].iloc[i]:
                        sell_ob = {'price': df['Low'].iloc[i], 'index': i}
                        break
    
    # ===== 2. شناسایی FVG (Fair Value Gap) =====
    fvg_up = None
    fvg_down = None
    
    if len(df) >= 5:
        for i in range(len(df)-3, 0, -1):
            # FVG صعودی
            if df['Low'].iloc[i] > df['High'].iloc[i+1] and df['High'].iloc[i-1] < df['Low'].iloc[i]:
                if current < df['Low'].iloc[i] and current > df['High'].iloc[i+1]:
                    fvg_up = {'upper': df['Low'].iloc[i], 'lower': df['High'].iloc[i+1]}
                    break
            
            # FVG نزولی
            if df['High'].iloc[i] < df['Low'].iloc[i+1] and df['Low'].iloc[i-1] > df['High'].iloc[i]:
                if current > df['High'].iloc[i] and current < df['Low'].iloc[i+1]:
                    fvg_down = {'upper': df['Low'].iloc[i+1], 'lower': df['High'].iloc[i]}
                    break
    
    # ===== 3. شناسایی Liquidity Sweep =====
    buy_sweep = False
    sell_sweep = False
    
    if len(high) > 30:
        # شکار نقدینگی خرید: قیمت به بالاترین حد رسیده و برگشته
        highest = max(high[-30:])
        if current < highest - 5 and high[-1] > highest - 2:
            buy_sweep = True
        
        # شکار نقدینگی فروش: قیمت به پایین‌ترین حد رسیده و برگشته
        lowest = min(low[-30:])
        if current > lowest + 5 and low[-1] < lowest + 2:
            sell_sweep = True
    
    # ===== 4. شناسایی Market Structure Shift =====
    mss_up = False
    mss_down = False
    
    if len(high) > 15:
        last_high = max(high[-5:])
        last_low = min(low[-5:])
        
        # تغییر ساختار صعودی
        if current > last_high and low[-1] > min(low[-10:-5]):
            mss_up = True
        
        # تغییر ساختار نزولی
        if current < last_low and high[-1] < max(high[-10:-5]):
            mss_down = True
    
    # ===== 5. تصمیم نهایی =====
    reasons = []
    score = 0
    direction = None
    
    # شرایط BUY
    buy_score = 0
    if buy_ob:
        buy_score += 35
        reasons.append(f"Order Block خرید در {buy_ob['price']:.2f}")
    if fvg_up:
        buy_score += 25
        reasons.append(f"FVG صعودی ({fvg_up['lower']:.2f} - {fvg_up['upper']:.2f})")
    if sell_sweep:
        buy_score += 20
        reasons.append("شکار نقدینگی فروش")
    if mss_up:
        buy_score += 20
        reasons.append("تغییر ساختار صعودی")
    
    # شرایط SELL
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
    
    # ===== 6. انتخاب جهت =====
    if buy_score >= 60 and buy_score > sell_score:
        direction = "BUY"
        score = buy_score
    elif sell_score >= 60 and sell_score > buy_score:
        direction = "SELL"
        score = sell_score
        reasons = sell_reasons
    else:
        return None, None
    
    # ===== 7. محاسبه Entry/SL/TP =====
    from database import get_setting
    rr_ratio = float(get_setting('rr_ratio') or '2')
    RISK = 5.0
    REWARD = RISK * rr_ratio
    
    # ورود دقیق‌تر با استفاده از Order Block
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
        'score': score
    }
    
    analysis = {
        'reasons': reasons,
        'score': score,
        'style': 'SMC'
    }
    
    return signal, analysis
