# signals.py
import requests
import os

def get_signal_from_api():
    """
    دریافت سیگنال از API (پشتیبان)
    """
    try:
        # از یاهو قیمت میگیریم
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "chart" in data and "result" in data["chart"]:
            result = data["chart"]["result"][0]
            meta = result["meta"]
            price = meta["regularMarketPrice"]
            
            # تولید سیگنال ساده
            if price > 2000:
                direction = "SELL"
                entry = price
                sl = round(price + 5, 2)
                tp = round(price - 8, 2)
            else:
                direction = "BUY"
                entry = price
                sl = round(price - 5, 2)
                tp = round(price + 8, 2)
            
            return {
                'direction': direction,
                'entry': round(entry, 2),
                'sl': sl,
                'tp': tp,
                'score': 70,
                'source': 'API (Yahoo)'
            }
        
        return None
        
    except Exception as e:
        print(f"API Error: {e}")
        return None

def create_signal(df=None, analysis=None):
    """
    ترکیبی: اول ICT، اگه نبود از API
    """
    try:
        # ===== مرحله 1: ICT =====
        if analysis is not None:
            # اگه تحلیل ICT وجود داره و کامل هست
            if isinstance(analysis, dict) and 'direction' in analysis:
                analysis['source'] = 'ICT Analysis'
                return analysis
        
        # ===== مرحله 2: API =====
        api_signal = get_signal_from_api()
        if api_signal:
            return api_signal
        
        # ===== مرحله 3: سیگنال پیش‌فرض =====
        return {
            'direction': 'BUY',
            'entry': 2000.00,
            'sl': 1995.00,
            'tp': 2008.00,
            'score': 50,
            'source': 'Default (Fallback)'
        }
        
    except Exception as e:
        print(f"Signal Error: {e}")
        return {
            'direction': 'BUY',
            'entry': 2000.00,
            'sl': 1995.00,
            'tp': 2008.00,
            'score': 50,
            'source': 'Default (Error)'
        }
