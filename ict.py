def ict_analysis(df):

    last = df.iloc[-1]

    prev = df.iloc[-2]


    buy = 0
    sell = 0

    buy_reason = []
    sell_reason = []



    # روند کوتاه مدت

    if last["close"] > prev["close"]:

        buy += 30
        buy_reason.append("Bullish Momentum")


    elif last["close"] < prev["close"]:

        sell += 30
        sell_reason.append("Bearish Momentum")




    # شکست سقف و کف اخیر

    high = df["high"].iloc[-10:-1].max()

    low = df["low"].iloc[-10:-1].min()



    if last["close"] > high:

        buy += 40
        buy_reason.append("BOS")



    if last["close"] < low:

        sell += 40
        sell_reason.append("BOS")





    # کندل قوی

    body = abs(
        last["close"] - last["open"]
    )

    size = last["high"] - last["low"]



    if size != 0 and body / size > 0.5:

        if last["close"] > last["open"]:

            buy += 30
            buy_reason.append("Displacement")


        else:

            sell += 30
            sell_reason.append("Displacement")





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
