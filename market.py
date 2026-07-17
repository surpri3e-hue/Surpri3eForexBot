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


def is_market_open():
    """
    بررسی می‌کنه آیا بازار طلا (XAU/USD) الان باز است یا بسته.

    قانون کلی بازار فارکس/طلا:
      - از یکشنبه ساعت ۲۲:۰۰ UTC باز می‌شه
      - تا جمعه ساعت ۲۲:۰۰ UTC باز می‌مونه
      - در این بازه، به‌جز حدود ۱ ساعت شکاف روزانه (rollover) که بین
        بروکرها متفاوته، معمولاً پیوسته بازه (اینجا برای سادگی و اطمینان
        در نظر گرفته نشده - فقط تعطیلی آخر هفته چک می‌شه)

    ⚠️ این تابع تعطیلات رسمی (کریسمس، سال نو و مشابه) را تشخیص نمی‌دهد،
    فقط الگوی هفتگی استاندارد بسته‌شدن بازار را چک می‌کند.
    """
    utc_now = datetime.now(pytz.utc)
    weekday = utc_now.weekday()  # دوشنبه=0 ... یکشنبه=6
    hour = utc_now.hour

    # جمعه از ساعت ۲۲:۰۰ UTC به بعد بسته است (جمعه weekday=4)
    if weekday == 4 and hour >= 22:
        return False
    # کل شنبه بسته است (weekday=5)
    if weekday == 5:
        return False
    # یکشنبه تا ساعت ۲۲:۰۰ UTC بسته است (یکشنبه weekday=6)
    if weekday == 6 and hour < 22:
        return False

    return True


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
            df.attrs['is_real_data'] = True
            print(f"✅ Twelve Data: {len(df)} کندل دریافت شد (دیتای واقعی)")
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
        df.attrs['is_real_data'] = False
        return df

    except Exception as e:
        print(f"❌ خطای تولید دیتای تست: {e}")
        return None


def get_historical_candles(start_date, end_date, timeframe="1h"):
    """
    دیتای کندلی تاریخی رو برای یک بازه‌ی زمانی مشخص می‌گیره (برای بک‌تست).

    پارامترها:
        start_date, end_date: رشته‌ی تاریخ به فرمت 'YYYY-MM-DD'
        timeframe: تایم‌فریم کندل‌ها (پیش‌فرض 1h، چون بازه‌های چندماهه
                   با کندل‌های کوچیک‌تر حجم دیتای خیلی زیادی می‌شه)

    خروجی: DataFrame با df.attrs['is_real_data']=True، یا None در صورت خطا.
    ⚠️ برخلاف get_gold_candles، این تابع fallback به دیتای تستی نداره -
    اگه دیتای واقعی در دسترس نباشه، صادقانه None برمی‌گردونه، چون
    بک‌تست روی دیتای تصادفی کاملاً بی‌معنیه.
    """
    if not TWELVE_DATA_KEY:
        print("⚠️ TWELVE_DATA_KEY تنظیم نشده - بک‌تست بدون دیتای واقعی ممکن نیست.")
        return None

    try:
        granularity = {
            "1min": "1min", "5min": "5min", "15min": "15min",
            "1h": "1h", "4h": "4h", "1d": "1day"
        }

        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": "XAU/USD",
            "interval": granularity.get(timeframe, "1h"),
            "start_date": start_date,
            "end_date": end_date,
            "apikey": TWELVE_DATA_KEY,
            "format": "json",
            "outputsize": 5000,  # سقف Twelve Data برای هر درخواست
        }

        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if "values" in data and len(data["values"]) > 0:
            df_data = []
            for candle in data["values"]:
                dt = pd.to_datetime(candle['datetime'])
                dt_tehran = dt.astimezone(TEHRAN_TZ) if dt.tzinfo else TEHRAN_TZ.localize(dt)

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
            df.attrs['is_real_data'] = True
            print(f"✅ دیتای تاریخی: {len(df)} کندل از {start_date} تا {end_date} دریافت شد")
            return df
        else:
            print(f"⚠️ دیتایی برای این بازه پیدا نشد: {data}")
            return None

    except Exception as e:
        print(f"❌ خطای دریافت دیتای تاریخی: {e}")
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
