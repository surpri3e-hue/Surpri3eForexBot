def find_fvg(df):

    for i in range(2, len(df)):

        # Bullish FVG
        if df["low"].iloc[i] > df["high"].iloc[i-2]:

            return {
                "type": "BUY",
                "high": df["high"].iloc[i-2],
                "low": df["low"].iloc[i]
            }


        # Bearish FVG
        if df["high"].iloc[i] < df["low"].iloc[i-2]:

            return {
                "type": "SELL",
                "high": df["high"].iloc[i],
                "low": df["low"].iloc[i-2]
            }


    return None



def detect_liquidity_sweep(df):

    last = df.iloc[-1]


    previous_high = df["high"].iloc[-20:-1].max()
    previous_low = df["low"].iloc[-20:-1].min()



    # Sweep High = احتمال فروش

    if (
        last["high"] > previous_high
        and last["close"] < previous_high
    ):

        return "SELL"



    # Sweep Low = احتمال خرید

    if (
        last["low"] < previous_low
        and last["close"] > previous_low
    ):

        return "BUY"



    return None




def detect_structure(df):

    last = df.iloc[-1]

    highs = df["high"].iloc[-6:-1]
    lows = df["low"].iloc[-6:-1]



    if last["close"] > highs.max():

        return "BUY"



    if last["close"] < lows.min():

        return "SELL"



    return None




def displacement(df):

    last = df.iloc[-1]


    body = abs(
        last["close"] - last["open"]
    )


    candle_range = (
        last["high"] - last["low"]
    )


    if candle_range == 0:
        return False



    # کندل قوی

    if body / candle_range > 0.6:

        return True


    return False





def ict_analysis(df):


    score_buy = 0
    score_sell = 0

    reasons_buy = []
    reasons_sell = []



    fvg = find_fvg(df)

    sweep = detect_liquidity_sweep(df)

    structure = detect_structure(df)



    # FVG

    if fvg:

        if fvg["type"] == "BUY":

            score_buy += 30
            reasons_buy.append("Bullish FVG")


        else:

            score_sell += 30
            reasons_sell.append("Bearish FVG")



    # Liquidity

    if sweep == "BUY":

        score_buy += 40
        reasons_buy.append("Liquidity Sweep")


    elif sweep == "SELL":

        score_sell += 40
        reasons_sell.append("Liquidity Sweep")



    # Structure

    if structure == "BUY":

        score_buy += 20
        reasons_buy.append("BOS/CHoCH")


    elif structure == "SELL":

        score_sell += 20
        reasons_sell.append("BOS/CHoCH")



    # Displacement

    if displacement(df):

        if score_buy > score_sell:

            score_buy += 10
            reasons_buy.append("Displacement")


        elif score_sell > score_buy:

            score_sell += 10
            reasons_sell.append("Displacement")




    # نتیجه نهایی


    if score_buy >= 70:

        return {

            "direction": "BUY",
            "score": score_buy,
            "reason": reasons_buy

        }




    if score_sell >= 70:

        return {

            "direction": "SELL",
            "score": score_sell,
            "reason": reasons_sell

        }



    return None
