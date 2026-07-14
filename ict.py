def find_fvg(df):

    # فقط FVG های نزدیک قیمت را بررسی می‌کنیم

    for i in range(len(df)-3, len(df)):

        # Bullish FVG

        if df["low"].iloc[i] > df["high"].iloc[i-2]:

            return {
                "type": "BUY"
            }



        # Bearish FVG

        if df["high"].iloc[i] < df["low"].iloc[i-2]:

            return {
                "type": "SELL"
            }


    return None





def liquidity_sweep(df):

    last = df.iloc[-1]


    highs = df["high"].iloc[-15:-1]

    lows = df["low"].iloc[-15:-1]



    if last["low"] < lows.min() and last["close"] > lows.min():

        return "BUY"



    if last["high"] > highs.max() and last["close"] < highs.max():

        return "SELL"



    return None





def market_structure(df):

    last = df.iloc[-1]


    recent_high = df["high"].iloc[-6:-1].max()

    recent_low = df["low"].iloc[-6:-1].min()



    if last["close"] > recent_high:

        return "BUY"



    if last["close"] < recent_low:

        return "SELL"



    return None





def displacement(df):

    last = df.iloc[-1]


    body = abs(
        last["close"] - last["open"]
    )


    total = last["high"] - last["low"]


    if total == 0:

        return False



    if body / total >= 0.5:

        return True



    return False





def ict_analysis(df):


    buy_score = 0
    sell_score = 0


    buy_reason = []
    sell_reason = []



    fvg = find_fvg(df)

    sweep = liquidity_sweep(df)

    structure = market_structure(df)





    # FVG

    if fvg:


        if fvg["type"] == "BUY":

            buy_score += 30

            buy_reason.append(
                "Bullish FVG"
            )


        else:

            sell_score += 30

            sell_reason.append(
                "Bearish FVG"
            )






    # Liquidity

    if sweep == "BUY":

        buy_score += 40

        buy_reason.append(
            "Liquidity Sweep"
        )



    elif sweep == "SELL":

        sell_score += 40

        sell_reason.append(
            "Liquidity Sweep"
        )







    # Structure

    if structure == "BUY":

        buy_score += 20

        buy_reason.append(
            "BOS"
        )



    elif structure == "SELL":

        sell_score += 20

        sell_reason.append(
            "BOS"
        )






    # Candle strength

    if displacement(df):


        if buy_score > sell_score:

            buy_score += 10

            buy_reason.append(
                "Displacement"
            )


        elif sell_score > buy_score:

            sell_score += 10

            sell_reason.append(
                "Displacement"
            )







    if buy_score >= 60:

        return {

            "direction":"BUY",

            "score":buy_score,

            "reason":buy_reason

        }





    if sell_score >= 60:

        return {

            "direction":"SELL",

            "score":sell_score,

            "reason":sell_reason

        }





    return None
