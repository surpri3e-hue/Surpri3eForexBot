import sqlite3
from datetime import datetime


DB_NAME = "trades.db"



def connect():

    return sqlite3.connect(DB_NAME)




def create_database():

    conn = connect()

    cursor = conn.cursor()


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        time TEXT,

        direction TEXT,

        entry REAL,

        sl REAL,

        tp REAL,

        score INTEGER,

        result TEXT DEFAULT 'OPEN',

        profit REAL DEFAULT 0

    )
    """)


    conn.commit()

    conn.close()






def save_trade(signal):

    conn = connect()

    cursor = conn.cursor()


    cursor.execute("""
    INSERT INTO trades
    (
        time,
        direction,
        entry,
        sl,
        tp,
        score
    )

    VALUES (?,?,?,?,?,?)
    """,

    (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        ),

        signal["direction"],

        signal["entry"],

        signal["sl"],

        signal["tp"],

        signal.get(
            "score",
            0
        )

    ))


    conn.commit()

    conn.close()






def update_result(trade_id, result):

    conn = connect()

    cursor = conn.cursor()


    profit = 0


    if result == "TP":

        profit = 2


    elif result == "SL":

        profit = -1



    cursor.execute("""
    UPDATE trades

    SET result=?,
        profit=?

    WHERE id=?
    """,

    (
        result,
        profit,
        trade_id
    ))



    conn.commit()

    conn.close()







def get_statistics():

    conn = connect()

    cursor = conn.cursor()


    cursor.execute("""
    SELECT result, profit
    FROM trades
    """)


    rows = cursor.fetchall()


    conn.close()



    total = len(rows)

    wins = 0

    losses = 0

    profit = 0

    loss = 0



    for r,p in rows:

        if r == "TP":

            wins += 1

            profit += p



        elif r == "SL":

            losses += 1

            loss += abs(p)



    winrate = 0


    if total > 0:

        winrate = round(
            (wins / total) * 100,
            2
        )



    pf = 0


    if loss > 0:

        pf = round(
            profit / loss,
            2
        )



    return {

        "trades": total,

        "wins": wins,

        "losses": losses,

        "winrate": winrate,

        "profit_factor": pf

    }
