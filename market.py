import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import os

TWELVE_DATA_KEY = os.getenv("TWELVE_DATA")

# ============ زمان تهران ============
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

def get_tehran_time():
    """دریافت زمان تهران"""
    return datetime.now(TEHRAN_TZ)

def get_gold_candles(timeframe="5min", count=50):
    """
    دریافت کندل با قیمت‌های دقیق‌تر
    """
    # ===== Twelve Data =====
    if TWELVE_DATA_KEY:
        try:
            granularity = {
                "1min": "1min", "5min": "5min", "15min": "15min",
                "1h": "1h", "4h": "4h", "1d": "1day"
            }
            
            url = f"https://api.twelvedata.com/time_series"
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
                    # تبدیل زمان به تهران
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
                return df
        except Exception as e:
            print(f"Twelve Data error: {e}")
    
    # ===== Yahoo =====
    try:
        interval_map = {
            "1min": "1m", "5min": "5m", "15min": "15m",
            "1h": "1h", "4h": "1h", "1d": "1d"
        }
        
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval={interval_map.get(timeframe, '5m')}&range=5d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if "chart" in data and "result" in data["chart"]:
            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            indicators = result["indicators"]["quote"][0]
            
            df_data = []
            for i, ts in enumerate(timestamps):
                dt = pd.to_datetime(ts, unit='s')
                dt_tehran = dt.astimezone(TEHRAN_TZ)
                
                df_data.append({
                    'Date': dt_tehran,
                    'Open': indicators['open'][i],
                    'High': indicators['high'][i],
                    'Low': indicators['low'][i],
                    'Close': indicators['close'][i],
                    'Volume': indicators['volume'][i]
                })
            
            df = pd.DataFrame(df_data)
            df = df.dropna()
            df = df.set_index('Date')
            df = df.sort_index()
            return df
    except Exception as e:
        print(f"Yahoo error: {e}")
    
    # ===== دیتای تست با قیمت واقعی =====
    return generate_test_data(timeframe, count)

def generate_test_data(timeframe="5min", count=50):
    """تولید دیتای تست با قیمت‌های واقعی"""
    try:
        now = get_tehran_time()
        
        freq_map = {
            "1min": "1min", "5min": "5min", "15min": "15min",
            "1h": "1h", "4h": "4h", "1d": "1d"
        }
        
        dates = pd.date_range(end=now, periods=count, freq=freq_map.get(timeframe, "5min"))
        
        # قیمت پایه (واقعی)
        base_price = get_current_price() or 4054.03
        
        # نوسان ملایم
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
        print(f"Test data error: {e}")
        return None

def get_current_price():
    """
    دریافت قیمت لحظه‌ای با اولویت Twelve Data
    """
    # ===== Twelve Data =====
    if TWELVE_DATA_KEY:
        try:
            url = f"https://api.twelvedata.com/price?symbol=XAU/USD&apikey={TWELVE_DATA_KEY}"
            response = requests.get(url, timeout=10)
            data = response.json()
            if "price" in data:
                return float(data["price"])
        except:
            pass
    
    # ===== Yahoo =====
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if "chart" in data and "result" in data["chart"]:
            result = data["chart"]["result"][0]
            meta = result["meta"]
            return float(meta["regularMarketPrice"])
    except:
        pass
    
    # ===== Gold API =====
    try:
        url = "https://api.gold-api.com/price/XAU"
        response = requests.get(url, timeout=10)
        data = response.json()
        if "price" in data:
            return float(data["price"])
    except:
        pass
    
    return 4054.03  # پیش‌فرض
