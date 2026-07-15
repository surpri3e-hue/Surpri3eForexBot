# ict.py
import pandas as pd
import numpy as np

def ict_analysis(df):
    """
    تحلیل ICT برای تشخیص Buy/Sell
    """
    try:
        if df is None or len(df) < 5:
            return None
        
        # گرفتن قیمت‌ها
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        
        # قیمت فعلی و قبلی
        current_price = close[-1]
        prev_price = close[-2]
        
        # میانگین متحرک ساده
        ma5 = np.mean(close[-5:])
        ma10 = np.mean(close[-10:]) if len(close) >= 10 else ma5
        
        # تشخیص روند
        if current_price > ma5 and ma5 > ma10:
            direction = "BUY"
            entry = round(current_price + 0.5, 2)
            sl = round(min(low[-5:]) - 2, 2)
            tp = round(max(high[-5:]) + 3, 2)
            score = 80
            
        elif current_price < ma5 and ma5 < ma10:
            direction = "SELL"
            entry = round(current_price - 0.5, 2)
            sl = round(max(high[-5:]) + 2, 2)
            tp = round(min(low[-5:]) - 3, 2)
            score = 80
            
        else:
            # بر اساس تغییر قیمت
            price_change = ((current_price - prev_price) / prev_price) * 100
            
            if price_change > 0.1:
                direction = "BUY"
                entry = round(current_price + 0.3, 2)
                sl = round(current_price - 3, 2)
                tp = round(current_price + 5, 2)
                score = 65
            elif price_change < -0.1:
                direction = "SELL"
                entry = round(current_price - 0.3, 2)
                sl = round(current_price + 3, 2)
                tp = round(current_price - 5, 2)
                score = 65
            else:
                direction = "BUY"
                entry = round(current_price + 0.5, 2)
                sl = round(current_price - 3, 2)
                tp = round(current_price + 5, 2)
                score = 60
        
        # اطمینان از منطقی بودن SL و TP
        if direction == "BUY":
            if sl >= entry:
                sl = round(entry - 2, 2)
            if tp <= entry:
                tp = round(entry + 4, 2)
        else:
            if sl <= entry:
                sl = round(entry + 2, 2)
            if tp >= entry:
                tp = round(entry - 4, 2)
        
        return {
            'direction': direction,
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'score': score
        }
        
    except Exception as e:
        print(f"ICT Error: {e}")
        return None
