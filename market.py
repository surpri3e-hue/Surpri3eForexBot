# market.py
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# ===== تنظیمات Twelve Data =====
TWELVE_DATA_KEY = os.getenv("TWELVE_DATA")

def get_gold_candles(timeframe="5min", count=50):
    """
    دریافت کندل‌ها: اول Twelve Data، بعد یاهو
    """
    # ===== منبع 1: Twelve Data =====
    if TWELVE_DATA_KEY:
        try:
            granularity_map = {
                "1min": "1min",
                "5min": "5min",
                "15min": "15min",
                "1h": "1h",
                "4h": "4h",
                "1d": "1day"
            }
            interval = granularity_map.get(timeframe, "5min")
            
            url = f"https://api.twelvedata.com/time_series"
            params = {
                "symbol": "XAU/USD",
                "interval": interval,
                "outputsize": count,
                "apikey": TWELVE_DATA_KEY,
                "format": "json"
            }
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if "values" in data and len(data["values"]) > 0:
                df_data = []
                for candle in data["values"]:
                    df_data.append({
                        'Date': pd.to_datetime(candle['datetime']),
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
        except Exception as e:
            print(f"❌ Twelve Data error: {e}")
    
    # ===== منبع 2: یاهو =====
    try:
        end = datetime.now()
        
        interval_map = {
            "1min": "1m",
            "5min": "5m",
            "15min": "15m",
            "1h": "1h",
            "4h": "1h",
            "1d": "1d"
        }
        interval = interval_map.get(timeframe, "5m")
        
        # برای 4h از 1h استفاده میکنیم و بعد جمع میکنیم
        if timeframe == "4h":
            return get_4h_candles_from_1h(count)
        
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval={interval}&range=5d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
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
                print(f"✅ Yahoo: {len(df)} candles received")
                return df
    except Exception as e:
        print(f"❌ Yahoo error: {e}")
    
    # ===== منبع 3: دیتای تست =====
    print("⚠️ Using test data")
    return generate_test_data(timeframe, count)

def get_4h_candles_from_1h(count=50):
    """
    گرفتن 1h از یاهو و تبدیل به 4h
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1h&range=10d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
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
            
            if len(df) > 10:
                # تبدیل به 4 ساعت
                df_4h = df.resample('4h').agg({
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Volume': 'sum'
                }).dropna()
                
                df_4h = df_4h.tail(count)
                print(f"✅ Yahoo (4h): {len(df_4h)} candles received")
                return df_4h
    except Exception as e:
        print(f"❌ 4h conversion error: {e}")
    
    return None

def generate_test_data(timeframe="5min", count=50):
    """
    تولید دیتای تست
    """
    try:
        now = datetime.now()
        
        freq_map = {
            "1min": "1min",
            "5min": "5min",
            "15min": "15min",
            "1h": "1h",
            "4h": "4h",
            "1d": "1d"
        }
        freq = freq_map.get(timeframe, "5min")
        
        dates = pd.date_range(end=now, periods=count, freq=freq)
        
        base_price = 2000 + np.random.randn() * 30
        trend = np.cumsum(np.random.randn(count) * 2)
        close = base_price + trend
        
        high = close + np.abs(np.random.randn(count) * 3 + 2)
        low = close - np.abs(np.random.randn(count) * 3 + 2)
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
    دریافت قیمت لحظه‌ای
    """
    # ===== از Twelve Data =====
    if TWELVE_DATA_KEY:
        try:
            url = f"https://api.twelvedata.com/price?symbol=XAU/USD&apikey={TWELVE_DATA_KEY}"
            response = requests.get(url, timeout=10)
            data = response.json()
            if "price" in data:
                return float(data["price"])
        except:
            pass
    
    # ===== از یاهو =====
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
    
    return None
