import matplotlib.pyplot as plt
import pandas as pd


def create_chart(df, signal, timeframe):

    filename = "chart.png"


    plt.figure(figsize=(12,6))


    # رسم کندل به صورت ساده
    plt.plot(
        df["close"],
        label="XAUUSD"
    )


    entry = signal["entry"]
    sl = signal["sl"]
    tp = signal["tp"]


    plt.axhline(
        entry,
        linestyle="--",
        label=f"Entry {entry}"
    )


    plt.axhline(
        sl,
        linestyle="--",
        label=f"SL {sl}"
    )


    plt.axhline(
        tp,
        linestyle="--",
        label=f"TP {tp}"
    )


    plt.title(
        f"XAUUSD {timeframe} ICT Setup"
    )


    plt.legend()


    plt.savefig(
        filename,
        dpi=300,
        bbox_inches="tight"
    )


    plt.close()


    return filename
