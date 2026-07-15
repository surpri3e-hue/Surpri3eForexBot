import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

def get_gold_candles(timeframe="5min"):
    """
    دریافت دیتای طلا از یاهو
    """
    try:
        # تنظیم بازه زمانی
        end = datetime.now()
        
        if timeframe == "1min":
            start = end - timedelta(days=1)
            interval = "1m"
        elif timeframe == "5min":
            start = end - timedelta(days=2)
            interval = "5m"
        elif timeframe == "15min":
            start = end - timedelta(days=5)
            interval = "15m"
        elif timeframe == "1h":
            start = end - timedelta(days=10)
            interval = "1h"
        elif timeframe == "4h":
            start = end - timedelta(days=20)
            interval = "1h"  # یاهو 4h نداره، از 1h استفاده میکنیم
        elif timeframe == "1d":
            start = end - timedelta(days=60)
            interval = "1d"
        else:
            start = end - timedelta(days=2)
            interval = "5m"
        
        # دریافت دیتا از یاهو
        gold = yf.Ticker("GC=F")
        df = gold.history(start=start, end=end, interval=interval)
        
        if df is not None and len(df) > 0:
            # پاکسازی دیتا
            df = df.dropna()
            if len(df) > 0:
                return df
        
        # اگر یاهو کار نکرد، دیتای تست
        print("⚠️ Yahoo data failed, using test data")
        return generate_test_data(timeframe)
        
    except Exception as e:
        print(f"❌ Market error: {e}")
        return generate_test_data(timeframe)

def generate_test_data(timeframe="5min"):
    """
    دیتای تست واقع‌گرایانه
    """
    try:
        periods = 50
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
        
        dates = pd.date_range(end=now, periods=periods, freq=freq)
        
        # قیمت با روند
        base = 2000 + np.random.randn() * 30
        trend = np.cumsum(np.random.randn(periods) * 1.5)
        close = base + trend
        
        high = close + np.abs(np.random.randn(periods) * 2 + 1)
        low = close - np.abs(np.random.randn(periods) * 2 + 1)
        open_price = close - np.random.randn(periods) * 0.5
        
        data = {
            'Open': open_price,
            'High': high,
            'Low': low,
            'Close': close,
            'Volume': np.random.randint(100, 1000, periods)
        }
        
        df = pd.DataFrame(data, index=dates)
        df = df.dropna()
        return df
        
    except Exception as e:
        print(f"❌ Test data error: {e}")
        return None
