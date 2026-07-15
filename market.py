# market.py
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def get_gold_price():
    """
    دریافت قیمت لحظه‌ای طلا از چند منبع
    """
    # ===== منبع 1: یاهو =====
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if "chart" in data and "result" in data["chart"]:
            result = data["chart"]["result"][0]
            meta = result["meta"]
            price = meta.get("regularMarketPrice")
            if price:
                return float(price)
    except:
        pass
    
    # ===== منبع 2: Twelve Data =====
    try:
        api_key = os.getenv("TWELVE_DATA")
        if api_key:
            url = f"https://api.twelvedata.com/price?symbol=XAU/USD&apikey={api_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            if "price" in data:
                return float(data["price"])
    except:
        pass
    
    # ===== منبع 3: Gold API (رایگان) =====
    try:
        url = "https://api.gold-api.com/price/XAU"
        response = requests.get(url, timeout=10)
        data = response.json()
        if "price" in data:
            return float(data["price"])
    except:
        pass
    
    # ===== منبع 4: Metal Price API =====
    try:
        url = "https://api.metalpriceapi.com/v1/latest?api_key=demo&base=USD&currencies=XAU"
        response = requests.get(url, timeout=10)
        data = response.json()
        if "rates" in data and "XAU" in data["rates"]:
            return float(data["rates"]["XAU"])
    except:
        pass
    
    # ===== آخرین راه: مقدار پیش‌فرض =====
    return 2000.00

def get_gold_candles(timeframe="5min"):
    """
    دریافت دیتای کندلی با قیمت‌های بروز
    """
    try:
        end = datetime.now()
        
        # تنظیم بازه زمانی
        interval_map = {
            "1min": "1m",
            "5min": "5m",
            "15min": "15m",
            "1h": "1h",
            "4h": "1h",
            "1d": "1d"
        }
        
        interval = interval_map.get(timeframe, "5m")
        
        # دریافت از یاهو
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval={interval}&range=5d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        if "chart" in data and "result" in data["chart"]:
            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            indicators = result["indicators"]["quote"][0]
            
            df = pd.DataFrame({
                'Date': pd.to_datetime(timestamps, unit='s'),
                'Open': indicators['open'],
                'High': indicators['high'],
                'Low': indicators['low'],
                'Close': indicators['close'],
                'Volume': indicators['volume']
            })
            
            df = df.dropna()
            df = df.set_index('Date')
            df = df.sort_index()
            
            if len(df) > 5:
                return df
        
        return None
        
    except Exception as e:
        print(f"Candles error: {e}")
        return None

def get_current_price():
    """
    دریافت قیمت لحظه‌ای (برای نمایش)
    """
    try:
        # تلاش از یاهو
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if "chart" in data and "result" in data["chart"]:
            result = data["chart"]["result"][0]
            meta = result["meta"]
            return float(meta["regularMarketPrice"])
        
        return None
        
    except:
        return None
