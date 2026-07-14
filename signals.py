def create_signal(df, analysis):

    if analysis is None:
        return None


    direction = analysis.get("direction")


    if direction not in ["BUY", "SELL"]:
        return None



    last = df.iloc[-1]

    entry = float(last["close"])



    if direction == "BUY":

        sl = float(
            df["low"].iloc[-10:].min()
        )


        risk = entry - sl


        if risk <= 0:
            return None


        tp = entry + (risk * 2)



    else:

        sl = float(
            df["high"].iloc[-10:].max()
        )


        risk = sl - entry


        if risk <= 0:
            return None


        tp = entry - (risk * 2)





    return {

        "direction": direction,

        "entry": round(entry, 2),

        "sl": round(sl, 2),

        "tp": round(tp, 2),

        "rr": "1:2",

        "score": analysis.get(
            "score",
            0
        ),

        "reason": analysis.get(
            "reason",
            []
        )

    }
