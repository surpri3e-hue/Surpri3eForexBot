def create_signal(df, analysis):

    if analysis is None:
        return None


    if analysis.get("direction") == "NONE":
        return None


    last = df.iloc[-1]

    entry = float(last["close"])



    if analysis["direction"] == "BUY":

        sl = float(
            df["low"].iloc[-10:].min()
        )

        risk = entry - sl


        if risk <= 0:
            return None


        tp = entry + (risk * 2)



    elif analysis["direction"] == "SELL":

        sl = float(
            df["high"].iloc[-10:].max()
        )

        risk = sl - entry


        if risk <= 0:
            return None


        tp = entry - (risk * 2)



    else:
        return None



    return {

        "direction": analysis["direction"],

        "entry": round(entry, 2),

        "sl": round(sl, 2),

        "tp": round(tp, 2),

        "rr": "1:2",

        "score": analysis.get("score", 0),

        "reason": analysis.get(
            "reason",
            []
        )

    }
