def create_signal(df, analysis):

    if analysis is None:
        return None

    last = df.iloc[-1]

    entry = last["close"]

    if analysis["direction"] == "BUY":

        sl = df["low"].iloc[-10:].min()

        risk = entry - sl

        if risk <= 0:
            return None

        tp = entry + (risk * 2)


    elif analysis["direction"] == "SELL":

        sl = df["high"].iloc[-10:].max()

        risk = sl - entry

        if risk <= 0:
            return None

        tp = entry - (risk * 2)


    return {
        "direction": analysis["direction"],
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "rr": "1:2",
        "reason": analysis["reason"]
    }
