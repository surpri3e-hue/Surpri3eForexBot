from database import get_open_trades, update_result
from market import get_gold_candles



def check_trades():

    trades = get_open_trades()


    if not trades:

        return



    df = get_gold_candles(
        "1min"
    )


    if df is None:

        return



    price = float(
        df["close"].iloc[-1]
    )



    for trade in trades:


        trade_id = trade[0]

        direction = trade[2]

        sl = trade[4]

        tp = trade[5]



        # BUY

        if direction == "BUY":


            if price >= tp:

                update_result(
                    trade_id,
                    "TP"
                )


            elif price <= sl:

                update_result(
                    trade_id,
                    "SL"
                )





        # SELL

        elif direction == "SELL":


            if price <= tp:

                update_result(
                    trade_id,
                    "TP"
                )


            elif price >= sl:

                update_result(
                    trade_id,
                    "SL"
                )
