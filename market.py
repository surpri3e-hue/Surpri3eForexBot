import requests
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import os

TEHRAN_TZ = pytz.timezone('Asia/Tehran')
TWELVE_DATA_KEY = os.getenv("TWELVE_DATA")


def get_tehran_time():
    return datetime.now(TEHRAN_TZ)


def get_gold_candles(timeframe="5min", count=50):
    """
    دیتای کندلی طلا رو برمی‌گردونه.
    df.attrs['is_real_data'] مشخص می‌کنه دیتا از Twelve Data اومده (True)
    یا دیتای تستی/شبیه‌سازی‌شده هست (False).
    ⚠️ همیشه قبل از تحلیل این پرچم رو چک کن - دیتای تستی رندومه و
    هیچ سیگنالی روش معتبر نیست.
    """
    if not TWELVE_DATA_KEY:
        print("⚠️ TWELVE_DATA_KEY تنظیم نشده! از دیتای تستی استفاده می‌شود.")
        return generate_test_data(timeframe, count)

    try:
        granularity = {
            "1min": "1min", "5min": "5min", "15min": "15min",
            "1h": "1h", "4h": "4h", "1d": "1day"
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
            
            # 🔥 کلید حل مشکل Repaint و پرش سیگنال:
            # حذف کندل آخر که هنوز بسته نشده و در حال نوسان است
            df = df.iloc[:-1]
            
            df.attrs['is_real_data'] = True
            print(f"✅ Twelve Data: {len(df)} کندل تثبیت‌شده دریافت شد (دیتای واقعی)")
            return df
        else:
            print(f"⚠️ پاسخ نامعتبر از Twelve Data: {data}")
            return generate_test_data(timeframe, count)

    except Exception as e:
        print(f"❌ خطای Twelve Data: {e}")
        return generate_test_data(timeframe, count)


def generate_test_data(timeframe="5min", count=50):
    """
    ⚠️ دیتای تصادفی شبیه‌سازی‌شده - فقط برای تست ساختار کد.
    هیچ سیگنالی که روی این دیتا تولید بشه معتبر نیست چون کاملاً نویز رندومه.
    """
    try:
        now = get_tehran_time()

        freq_map = {
            "1min": "1min", "5min": "5min", "15min": "15min",
            "1h": "1h", "4h": "4h", "1d": "1d"
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
        
        # 🔥 حذف کندل لایو از دیتای تستی برای هماهنگی با رفتار واقعی
        df = df.iloc[:-1]
        
        df.attrs['is_real_data'] = False
        return df

    except Exception as e:
        print(f"❌ خطای تولید دیتای تست: {e}")
        return None


def get_current_price():
    # ===== منبع 1: GoldAPI =====
    try:
        url = "https://api.gold-api.com/price/XAU"
        response = requests.get(url, timeout=10)
        data = response.json()
        if "price" in data:
            price = float(data["price"])
            print(f"✅ GoldAPI: {price}")
            return round(price, 2)
    except Exception as e:
        print(f"❌ خطای GoldAPI: {e}")

    # ===== منبع 2: Twelve Data =====
    if TWELVE_DATA_KEY:
        try:
            url = "https://api.twelvedata.com/price"
            params = {
                "symbol": "XAU/USD",
                "apikey": TWELVE_DATA_KEY
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if "price" in data:
                price = float(data["price"])
                print(f"✅ Twelve Data: {price}")
                return round(price, 2)
        except Exception as e:
            print(f"❌ خطای Twelve Data: {e}")

    return None
