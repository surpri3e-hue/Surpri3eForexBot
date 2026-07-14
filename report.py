from database import get_trades


def create_report():

    trades = get_trades()


    total = len(trades)

    tp = 0
    sl = 0
    active = 0



    for trade in trades:

        result = trade[7]


        if result == "TP":
            tp += 1

        elif result == "SL":
            sl += 1

        elif result == "ACTIVE":
            active += 1




    finished = tp + sl


    if finished > 0:

        winrate = round(
            (tp / finished) * 100,
            2
        )

    else:

        winrate = 0




    # Profit Factor ساده بر اساس RR 1:2

    profit = tp * 2

    loss = sl * 1


    if loss > 0:

        pf = round(
            profit / loss,
            2
        )

    else:

        pf = 0




    return f"""
📊 Surpri3e AI Report


Total Signals:
{total}


TP Hit:
✅ {tp}


SL Hit:
❌ {sl}


Active:
⏳ {active}


Win Rate:
{winrate}%


Profit Factor:
{pf}
"""
