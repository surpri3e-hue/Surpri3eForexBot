import os
import requests
import pandas as pd


API_KEY = os.getenv("TWELVE_API_KEY")


def get_gold_candles(interval):

    url = "https://api.twelvedata.com/time_series"


    params = {

        "symbol": "XAU/USD",

        "interval": interval,

        "outputsize": 100,

        "apikey": API_KEY,

        "timezone": "UTC"

    }


    try:

        response = requests.get(
            url,
            params=params,
            timeout=15
        )


        data = response.json()



        if "values" not in data:

            print(data)

            return None




        df = pd.DataFrame(
            data["values"]
        )



        df["open"] = df["open"].astype(float)

        df["high"] = df["high"].astype(float)

        df["low"] = df["low"].astype(float)

        df["close"] = df["close"].astype(float)



        df = df.iloc[::-1].reset_index(drop=True)



        print(
            "LATEST GOLD PRICE:",
            df["close"].iloc[-1]
        )



        return df




    except Exception as e:

        print(
            "MARKET ERROR:",
            e
        )

        return None
