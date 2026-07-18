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


def is_market_open(symbol="XAU/USD"):
    """
    بررسی می‌کنه آیا بازار برای نماد داده‌شده الان باز است یا بسته.

    ⚠️ این چک فقط برای بازارهای فارکس/کالا (مثل طلا) معناداره؛ بازار
    کریپتو (مثل بیت‌کوین) ۲۴/۷ باز است و هیچ‌وقت تعطیل نمی‌شه، پس برای
    نمادهای کریپتو همیشه True برمی‌گردونه.

    قانون کلی بازار فارکس/طلا:
      - از یکشنبه ساعت ۲۲:۰۰ UTC باز می‌شه
      - تا جمعه ساعت ۲۲:۰۰ UTC باز می‌مونه
      - در این بازه، به‌جز حدود ۱ ساعت شکاف روزانه (rollover) که بین
        بروکرها متفاوته، معمولاً پیوسته بازه (اینجا برای سادگی و اطمینان
        در نظر گرفته نشده - فقط تعطیلی آخر هفته چک می‌شه)

    ⚠️ این تابع تعطیلات رسمی (کریسمس، سال نو و مشابه) را تشخیص نمی‌دهد،
    فقط الگوی هفتگی استاندارد بسته‌شدن بازار فارکس/طلا را چک می‌کند.
    """
    # ===== نمادهای کریپتو ۲۴/۷ باز هستن - هیچ‌وقت بسته نمی‌شن =====
    CRYPTO_SYMBOLS = {"BTC/USD", "ETH/USD"}
    if symbol.upper() in CRYPTO_SYMBOLS:
        return True

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


def get_gold_candles(timeframe="5min", count=50, symbol="XAU/USD"):
    """
    دیتای کندلی رو برای نماد مشخص‌شده برمی‌گردونه (پیش‌فرض طلا).
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
            "symbol": symbol,
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
            print(f"✅ Twelve Data ({symbol}): {len(df)} کندل دریافت شد (دیتای واقعی)")
            return df
        else:
            print(f"⚠️ پاسخ نامعتبر از Twelve Data برای {symbol}: {data}")
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


def get_historical_candles(start_date, end_date, timeframe="1h", symbol="XAU/USD"):
    """
    دیتای کندلی تاریخی رو برای یک بازه‌ی زمانی مشخص می‌گیره (برای بک‌تست).

    پارامترها:
        start_date, end_date: رشته‌ی تاریخ به فرمت 'YYYY-MM-DD'
        timeframe: تایم‌فریم کندل‌ها (پیش‌فرض 1h)
        symbol: نماد Twelve Data (مثلاً 'XAU/USD' یا 'BTC/USD')

    خروجی: (df, error_message)
        اگه موفق بود: (DataFrame با is_real_data=True، None)
        اگه ناموفق بود: (None، متن دقیق خطا برای نمایش به کاربر)
    """
    if not TWELVE_DATA_KEY:
        return None, "کلید TWELVE_DATA در متغیرهای محیطی تنظیم نشده است."

    try:
        granularity = {
            "1min": "1min", "5min": "5min", "15min": "15min",
            "1h": "1h", "4h": "4h", "1d": "1day"
        }

        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": symbol,
            "interval": granularity.get(timeframe, "1h"),
            "start_date": start_date,
            "end_date": end_date,
            "apikey": TWELVE_DATA_KEY,
            "format": "json",
            "outputsize": 5000,  # سقف Twelve Data برای هر درخواست
        }

        response = requests.get(url, params=params, timeout=30)

        try:
            data = response.json()
        except ValueError:
            return None, f"پاسخ نامعتبر از سرور Twelve Data (کد HTTP: {response.status_code})."

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
            return df, None
        else:
            # ===== پیام خطای واقعی API رو استخراج و برگردون، نه فقط لاگ کن =====
            api_message = data.get("message") or data.get("status") or str(data)
            print(f"⚠️ دیتایی برای این بازه پیدا نشد: {data}")
            return None, api_message

    except Exception as e:
        print(f"❌ خطای دریافت دیتای تاریخی: {e}")
        return None, str(e)


def get_current_price(symbol="XAU/USD"):
    # ===== منبع 1: GoldAPI (فقط برای طلا کار می‌کنه) =====
    if symbol == "XAU/USD":
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

    # ===== منبع 2: Twelve Data (برای همه‌ی نمادها) =====
    if TWELVE_DATA_KEY:
        try:
            url = "https://api.twelvedata.com/price"
            params = {
                "symbol": symbol,
                "apikey": TWELVE_DATA_KEY
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if "price" in data:
                price = float(data["price"])
                print(f"✅ Twelve Data ({symbol}): {price}")
                return round(price, 2)
        except Exception as e:
            print(f"❌ خطای Twelve Data: {e}")

    return None
