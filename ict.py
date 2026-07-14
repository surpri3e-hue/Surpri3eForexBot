def find_fvg(df):
    """
    Detect Fair Value Gap
    """

    for i in range(2, len(df)):

        # Bullish FVG
        if df["low"][i] > df["high"][i-2]:
            return {
                "type": "BUY",
                "index": i,
                "high": df["high"][i-2],
                "low": df["low"][i]
            }

        # Bearish FVG
        if df["high"][i] < df["low"][i-2]:
            return {
                "type": "SELL",
                "index": i,
                "high": df["high"][i],
                "low": df["low"][i-2]
            }

    return None



def detect_liquidity_sweep(df):

    last = df.iloc[-1]

    previous_high = df["high"].iloc[-10:-1].max()
    previous_low = df["low"].iloc[-10:-1].min()


    # Sweep high
    if last["high"] > previous_high and last["close"] < previous_high:
        return "SELL"


    # Sweep low
    if last["low"] < previous_low and last["close"] > previous_low:
        return "BUY"


    return None



def detect_structure(df):

    last = df.iloc[-1]
    previous = df.iloc[-5:-1]


    if last["close"] > previous["high"].max():
        return "BULLISH_BOS"


    if last["close"] < previous["low"].min():
        return "BEARISH_BOS"


    return None



def ict_analysis(df):

    fvg = find_fvg(df)
    sweep = detect_liquidity_sweep(df)
    structure = detect_structure(df)


    if not fvg or not sweep or not structure:
        return None


    # BUY setup
    if (
        fvg["type"] == "BUY"
        and sweep == "BUY"
        and structure == "BULLISH_BOS"
    ):
        return {
            "direction": "BUY",
            "reason": [
                "Liquidity Sweep",
                "Bullish FVG",
                "BOS"
            ]
        }


    # SELL setup
    if (
        fvg["type"] == "SELL"
        and sweep == "SELL"
        and structure == "BEARISH_BOS"
    ):
        return {
            "direction": "SELL",
            "reason": [
                "Liquidity Sweep",
                "Bearish FVG",
                "BOS"
            ]
        }


    return None
