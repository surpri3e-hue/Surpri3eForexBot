import requests
import pandas as pd
import numpy as np
from datetime import datetime
import os

TWELVE_DATA_KEY = os.getenv("TWELVE_DATA")

def get_gold_candles(timeframe="5min", count=50):
    if TWELVE_DATA_KEY:
        try:
            granularity = {"1min": "1min", "5min": "5min", "15min": "15min", "1h": "1h", "4h": "4h", "1d": "1day"}
            url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval={granularity.get(timeframe, '5min')}&outputsize={count}&apikey={TWELVE_DATA_KEY}"
            response = requests.get(url, timeout=10)
            data = response.json()

            if "values" in data:
                df = pd.DataFrame(data["values"])
                df = df.rename(columns={"datetime": "Date", "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
                df["Date"] = pd.to_datetime(df["Date"])
                df = df.set_index("Date")
                for col in ["Open", "High", "Low", "Close"]:
                    df[col] = pd.to_numeric(df[col])
                return df.sort_index()
        except:
            pass

    try:
        interval = {"1min": "1m", "5min": "5m", "15min": "15m", "1h": "1h", "4h": "1h", "1d": "1d"}
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval={interval.get(timeframe, '5m')}&range=5d"
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
            return df.sort_index()
    except:
        pass

    # دیتای تست
    now = datetime.now()
    freq = {"1min": "1min", "5min": "5min", "15min": "15min", "1h": "1h", "4h": "4h", "1d": "1d"}
    dates = pd.date_range(end=now, periods=count, freq=freq.get(timeframe, "5min"))
    base = 4054
    close = base + np.cumsum(np.random.randn(count) * 2)
    data = {
        'Open': close - np.random.randn(count),
        'High': close + abs(np.random.randn(count) * 2 + 1),
        'Low': close - abs(np.random.randn(count) * 2 + 1),
        'Close': close,
        'Volume': np.random.randint(100, 1000, count)
    }
    df = pd.DataFrame(data, index=dates)
    return df

def get_current_price():
    if TWELVE_DATA_KEY:
        try:
            url = f"https://api.twelvedata.com/price?symbol=XAU/USD&apikey={TWELVE_DATA_KEY}"
            response = requests.get(url, timeout=10)
            data = response.json()
            if "price" in data:
                return float(data["price"])
        except:
            pass

    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if "chart" in data and "result" in data["chart"]:
            return float(data["chart"]["result"][0]["meta"]["regularMarketPrice"])
    except:
        pass

    return None
