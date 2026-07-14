def find_fvg(df):

    for i in range(len(df)-5, len(df)):

        if df["low"].iloc[i] > df["high"].iloc[i-2]:
            return "BUY"

        if df["high"].iloc[i] < df["low"].iloc[i-2]:
            return "SELL"

    return None



def liquidity_sweep(df):

    last = df.iloc[-1]

    high = df["high"].iloc[-20:-1].max()
    low = df["low"].iloc[-20:-1].min()


    if last["low"] < low and last["close"] > low:
        return "BUY"


    if last["high"] > high and last["close"] < high:
        return "SELL"


    return None



def structure(df):

    last = df.iloc[-1]

    high = df["high"].iloc[-5:-1].max()
    low = df["low"].iloc[-5:-1].min()


    if last["close"] > high:
        return "BUY"


    if last["close"] < low:
        return "SELL"


    return None



def ict_analysis(df):

    buy = 0
    sell = 0

    buy_reason = []
    sell_reason = []


    fvg = find_fvg(df)
    sweep = liquidity_sweep(df)
    bos = structure(df)



    if fvg == "BUY":
        buy += 25
        buy_reason.append("FVG")


    if fvg == "SELL":
        sell += 25
        sell_reason.append("FVG")



    if sweep == "BUY":
        buy += 40
        buy_reason.append("Liquidity Sweep")


    if sweep == "SELL":
        sell += 40
        sell_reason.append("Liquidity Sweep")



    if bos == "BUY":
        buy += 35
        buy_reason.append("BOS")


    if bos == "SELL":
        sell += 35
        sell_reason.append("BOS")



    if buy >= 50:

        return {
            "direction":"BUY",
            "score":buy,
            "reason":buy_reason
        }


    if sell >= 50:

        return {
            "direction":"SELL",
            "score":sell,
            "reason":sell_reason
        }


    return None
