def detect_sweep(df):

    last = df.iloc[-1]

    high = df["high"].iloc[-20:-1].max()
    low = df["low"].iloc[-20:-1].min()


    if last["low"] < low and last["close"] > low:

        return "BUY"



    if last["high"] > high and last["close"] < high:

        return "SELL"



    return None





def detect_bos(df):

    last = df.iloc[-1]

    high = df["high"].iloc[-10:-1].max()
    low = df["low"].iloc[-10:-1].min()


    if last["close"] > high:

        return "BUY"



    if last["close"] < low:

        return "SELL"



    return None





def detect_fvg(df):

    last = len(df)-1


    if df["low"].iloc[last] > df["high"].iloc[last-2]:

        return "BUY"



    if df["high"].iloc[last] < df["low"].iloc[last-2]:

        return "SELL"



    return None





def strong_candle(df):

    candle = df.iloc[-1]


    body = abs(
        candle["close"] - candle["open"]
    )


    size = candle["high"] - candle["low"]


    if size == 0:

        return None



    if body / size >= 0.55:

        if candle["close"] > candle["open"]:

            return "BUY"

        else:

            return "SELL"



    return None





def ict_analysis(df):


    buy = 0
    sell = 0


    buy_reason = []
    sell_reason = []



    sweep = detect_sweep(df)

    bos = detect_bos(df)

    fvg = detect_fvg(df)

    candle = strong_candle(df)





    if sweep == "BUY":

        buy += 35
        buy_reason.append("Liquidity Sweep")



    if sweep == "SELL":

        sell += 35
        sell_reason.append("Liquidity Sweep")





    if bos == "BUY":

        buy += 30
        buy_reason.append("BOS")



    if bos == "SELL":

        sell += 30
        sell_reason.append("BOS")





    if fvg == "BUY":

        buy += 20
        buy_reason.append("FVG")



    if fvg == "SELL":

        sell += 20
        sell_reason.append("FVG")





    if candle == "BUY":

        buy += 15
        buy_reason.append("Strong Candle")



    if candle == "SELL":

        sell += 15
        sell_reason.append("Strong Candle")





    if buy >= 60:

        return {

            "direction":"BUY",

            "score":buy,

            "reason":buy_reason

        }





    if sell >= 60:

        return {

            "direction":"SELL",

            "score":sell,

            "reason":sell_reason

        }




    return None
