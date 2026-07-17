# market.py
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import os

TEHRAN_TZ = pytz.timezone('Asia/Tehran')
TWELVE_DATA_KEY = os.getenv("TWELVE_DATA")

def get_tehran_time():
    """دریافت زمان تهران"""
    return datetime.now(TEHRAN_TZ)

def is_market_open():
    """
    بررسی باز بودن بازار طلا (XAUUSD)
    بازار طلا از یکشنبه تا جمعه باز است.
    روز شنبه و ساعات ۲۰:۰۰ تا ۲۲:۰۰ (تهران) بسته است.
    """
    now = datetime.now(TEHRAN_TZ)
    
    # شنبه ها بسته است
    if now.weekday() == 5:  # 5 = شنبه
        return False
    
    # یکشنبه تا پنجشنبه باز است
    if now.weekday() in [0, 1, 2, 3, 4]:  # 0=یکشنبه, 4=پنجشنبه
        # ساعت ۲۰ تا ۲۲ بسته است (ریست سرورها)
        if 20 <= now.hour < 22:
            return False
        return True
    
    # جمعه ها بسته است
    if now.weekday() == 6:
        return False
    
    return True

def get_gold_candles(timeframe="5min", count=50):
    """
    دریافت کندل از Twelve Data
    """
    if not TWELVE_DATA_KEY:
        print("⚠️ TWELVE_DATA_KEY not set!")
        return generate_test_data(timeframe, count)
    
    try:
        granularity = {
            "1min": "1min",
            "5min": "5min",
            "15min": "15min",
            "1h": "1h",
            "4h": "4h",
            "1d": "1day"
        }
        
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": "XAU/USD",
            "interval": granularity.get(timeframe, "5min"),
            "outputsize": count,
            "apikey": TWELVE_DATA_KEY,
            "format": "json"
        }
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if "values" in data and len(data["values"]) > 0:
            df_data = []
            for candle in data["values"]:
                dt = pd.to_datetime(candle['datetime'])
                dt_tehran = dt.astimezone(TEHRAN_TZ)
                
                df_data.append({
                    'Date': dt_tehran,
                    'Open': float(candle['open']),
                    'High': float(candle['high']),
                    'Low': float(candle['low']),
                    'Close': float(candle['close']),
                    'Volume': int(candle.get('volume', 0))
                })
            
            df = pd.DataFrame(df_data)
            df = df.set_index('Date')
            df = df.sort_index()
            print(f"✅ Twelve Data: {len(df)} candles received")
            return df
        else:
            print("⚠️ No data from Twelve Data")
            return generate_test_data(timeframe, count)
            
    except Exception as e:
        print(f"❌ Twelve Data error: {e}")
        return generate_test_data(timeframe, count)

def generate_test_data(timeframe="5min", count=50):
    """تولید دیتای تست (فقط در صورت عدم دسترسی به Twelve Data)"""
    try:
        now = get_tehran_time()
        
        freq_map = {
            "1min": "1min",
            "5min": "5min",
            "15min": "15min",
            "1h": "1h",
            "4h": "4h",
            "1d": "1d"
        }
        
        dates = pd.date_range(end=now, periods=count, freq=freq_map.get(timeframe, "5min"))
        
        base_price = 4054.03
        noise = np.random.randn(count) * 3
        close = base_price + noise
        
        high = close + np.abs(np.random.randn(count) * 2 + 1.5)
        low = close - np.abs(np.random.randn(count) * 2 + 1.5)
        open_price = close - np.random.randn(count) * 1.5
        
        data = {
            'Open': open_price,
            'High': high,
            'Low': low,
            'Close': close,
            'Volume': np.random.randint(100, 1000, count)
        }
        
        df = pd.DataFrame(data, index=dates)
        df = df.dropna()
        return df
        
    except Exception as e:
        print(f"❌ Test data error: {e}")
        return None

def get_current_price():
    """
    دریافت قیمت لحظه‌ای از Twelve Data
    """
    if not TWELVE_DATA_KEY:
        return None
    
    try:
        url = f"https://api.twelvedata.com/price"
        params = {
            "symbol": "XAU/USD",
            "apikey": TWELVE_DATA_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "price" in data:
            return float(data["price"])
        else:
            return None
            
    except Exception as e:
        print(f"❌ Price error: {e}")
        return None
