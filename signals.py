# signals.py
import requests
import os
from market import get_current_price

def get_signal_from_api():
    """
    دریافت سیگنال از API با قیمت لحظه‌ای
    """
    try:
        # گرفتن قیمت لحظه‌ای
        price = get_current_price()
        
        if not price:
            return None
        
        # تولید سیگنال بر اساس قیمت لحظه‌ای
        if price > 2050:
            direction = "SELL"
            entry = price
            sl = round(price + 5, 2)
            tp = round(price - 10, 2)
        else:
            direction = "BUY"
            entry = price
            sl = round(price - 5, 2)
            tp = round(price + 10, 2)
        
        return {
            'direction': direction,
            'entry': round(entry, 2),
            'sl': sl,
            'tp': tp,
            'score': 75,
            'source': 'API (Live Price)'
        }
        
    except Exception as e:
        print(f"API Error: {e}")
        return None

def create_signal(df=None, analysis=None):
    """
    ترکیبی: اول ICT، اگه نبود از API با قیمت لحظه‌ای
    """
    try:
        # ===== مرحله 1: ICT =====
        if analysis is not None and isinstance(analysis, dict):
            if 'direction' in analysis:
                # بروز کردن قیمت ورود
                current_price = get_current_price()
                if current_price:
                    analysis['entry'] = round(current_price, 2)
                analysis['source'] = 'ICT Analysis'
                return analysis
        
        # ===== مرحله 2: API =====
        api_signal = get_signal_from_api()
        if api_signal:
            return api_signal
        
        # ===== مرحله 3: پیش‌فرض =====
        price = get_current_price() or 2000.00
        return {
            'direction': 'BUY',
            'entry': round(price, 2),
            'sl': round(price - 5, 2),
            'tp': round(price + 10, 2),
            'score': 50,
            'source': 'Default'
        }
        
    except Exception as e:
        print(f"Signal Error: {e}")
        return None
