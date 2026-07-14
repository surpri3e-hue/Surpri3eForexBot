def find_fvg(df):

    for i in range(len(df)-3, len(df)):

        # Bullish FVG

        if df["low"].iloc[i] > df["high"].iloc[i-2]:

            return "BUY"



        # Bearish FVG

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





def market_structure(df):

    last = df.iloc[-1]


    high = df["high"].iloc[-10:-1].max()

    low = df["low"].iloc[-10:-1].min()



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

    structure = market_structure(df)




    if fvg == "BUY":

        buy += 25

        buy_reason.append(
            "Bullish FVG"
        )


    elif fvg == "SELL":

        sell += 25

        sell_reason.append(
            "Bearish FVG"
        )




    if sweep == "BUY":

        buy += 40

        buy_reason.append(
            "Liquidity Sweep"
        )


    elif sweep == "SELL":

        sell += 40

        sell_reason.append(
            "Liquidity Sweep"
        )




    if structure == "BUY":

        buy += 35

        buy_reason.append(
            "BOS"
        )


    elif structure == "SELL":

        sell += 35

        sell_reason.append(
            "BOS"
        )





    if buy >= 70:

        return {

            "direction":"BUY",

            "score":buy,

            "reason":buy_reason

        }





    if sell >= 70:

        return {

            "direction":"SELL",

            "score":sell,

            "reason":sell_reason

        }




    return None
