import json
import os
from datetime import datetime


FILE = "trades.json"


def load_trades():

    if not os.path.exists(FILE):
        return []

    with open(FILE, "r") as f:
        return json.load(f)



def save_trade(signal):

    trades = load_trades()

    trade = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "direction": signal["direction"],
        "entry": signal["entry"],
        "sl": signal["sl"],
        "tp": signal["tp"],
        "rr": signal["rr"],
        "result": "ACTIVE"
    }

    trades.append(trade)

    with open(FILE, "w") as f:
        json.dump(trades, f, indent=4)



def update_result(index, result):

    trades = load_trades()

    if index < len(trades):
        trades[index]["result"] = result

    with open(FILE, "w") as f:
        json.dump(trades, f, indent=4)



def get_stats():

    trades = load_trades()

    total = len(trades)

    wins = len([t for t in trades if t["result"] == "TP"])
    losses = len([t for t in trades if t["result"] == "SL"])

    winrate = 0

    if total > 0:
        winrate = round((wins / total) * 100, 2)


    profit_factor = 0

    if losses > 0:
        profit_factor = round(
            (wins * 2) / losses,
            2
        )


    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "profit_factor": profit_factor
    }
