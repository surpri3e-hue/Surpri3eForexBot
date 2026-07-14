def ict_analysis(df):

    last = df.iloc[-1]

    return {
        "direction": "BUY",
        "score": 70,
        "reason": [
            f"Close: {last['close']}",
            f"High: {last['high']}",
            f"Low: {last['low']}"
        ]
    }
