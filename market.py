import os
import requests
import pandas as pd


API_KEY = os.getenv("TWELVE_API_KEY")


def get_gold_candles(interval):

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": "XAU/USD",
        "interval": interval,
        "outputsize": 200,
        "apikey": API_KEY
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        data = response.json()


        if "values" not in data:
            print("DATA ERROR:", data)
            return None


        df = pd.DataFrame(
            data["values"]
        )


        df = df.astype({
            "open": float,
            "high": float,
            "low": float,
            "close": float
        })


        # مرتب‌سازی از قدیمی به جدید
        df = df.iloc[::-1].reset_index(drop=True)


        return df



    except requests.exceptions.Timeout:

        print("API TIMEOUT")
        return None



    except Exception as e:

        print("MARKET ERROR:", e)
        return None
