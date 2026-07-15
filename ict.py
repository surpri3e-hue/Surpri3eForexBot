# ict.py
import pandas as pd
import numpy as np

def ict_analysis(df):
    """تحلیل ICT با تشخیص خرید و فروش"""
    try:
        if df is None or len(df) < 10:
            return None
        
        # محاسبه اندیکاتورها
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        # میانگین متحرک ساده
        ma_short = np.mean(close[-5:])
        ma_long = np.mean(close[-20:]) if len(close) >= 20 else ma_short
        
        # تشخیص روند
        current_price = close[-1]
        prev_price = close[-2]
        
        # تغییر قیمت
        price_change = (current_price - prev_price) / prev_price * 100
        
        # ساپورت و رزیستنس
        recent_high = max(high[-10:])
        recent_low = min(low[-10:])
        
        # ====== تشخیص جهت ======
        direction = "NEUTRAL"
        entry = current_price
        
        # شرط BUY
        if current_price < ma_short and price_change > 0.1:
            direction = "BUY"
            entry = current_price + 0.5
            sl = recent_low - 2
            tp = recent_high + 3
        
        # شرط SELL
        elif current_price > ma_short and price_change < -0.1:
            direction = "SELL"
            entry = current_price - 0.5
            sl = recent_high + 2
            tp = recent_low - 3
        
        # اگر شرایط واضح نبود، از روند استفاده کن
        else:
            if current_price > ma_long:
                direction = "BUY"
                entry = current_price + 0.5
                sl = recent_low - 2
                tp = recent_high + 3
            elif current_price < ma_long:
                direction = "SELL"
                entry = current_price - 0.5
                sl = recent_high + 2
                tp = recent_low - 3
        
        # اگه باز هم NEUTRAL بود، بر اساس تغییر قیمت تصمیم بگیر
        if direction == "NEUTRAL":
            if price_change > 0:
                direction = "BUY"
                entry = current_price + 0.5
                sl = recent_low - 2
                tp = recent_high + 3
            else:
                direction = "SELL"
                entry = current_price - 0.5
                sl = recent_high + 2
                tp = recent_low - 3
        
        # امتیاز سیگنال
        score = 70
        if abs(price_change) > 0.5:
            score = 85
        elif abs(price_change) > 0.2:
            score = 75
        
        return {
            'direction': direction,
            'entry': round(entry, 2),
            'sl': round(sl, 2),
            'tp': round(tp, 2),
            'score': score
        }
        
    except Exception as e:
        print(f"❌ ICT Analysis Error: {e}")
        return None
