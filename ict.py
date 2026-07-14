def ict_analysis(df):

    buy = 0
    sell = 0

    buy_reason = []
    sell_reason = []


    last = df.iloc[-1]


    high = df["high"].iloc[-20:-1].max()
    low = df["low"].iloc[-20:-1].min()



    # Liquidity Sweep

    if last["low"] < low and last["close"] > low:

        buy += 40
        buy_reason.append("Liquidity Sweep")


    if last["high"] > high and last["close"] < high:

        sell += 40
        sell_reason.append("Liquidity Sweep")




    # Structure

    recent_high = df["high"].iloc[-5:-1].max()
    recent_low = df["low"].iloc[-5:-1].min()



    if last["close"] > recent_high:

        buy += 35
        buy_reason.append("BOS")



    if last["close"] < recent_low:

        sell += 35
        sell_reason.append("BOS")





    # FVG ساده

    if df["low"].iloc[-1] > df["high"].iloc[-3]:

        buy += 25
        buy_reason.append("FVG")



    if df["high"].iloc[-1] < df["low"].iloc[-3]:

        sell += 25
        sell_reason.append("FVG")





    if buy >= sell:

        return {

            "direction": "BUY" if buy >= 50 else "NONE",

            "score": buy,

            "reason": buy_reason

        }



    else:

        return {

            "direction": "SELL" if sell >= 50 else "NONE",

            "score": sell,

            "reason": sell_reason

        }
