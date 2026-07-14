import sqlite3
from datetime import datetime


DB = "trades.db"



def connect():

    return sqlite3.connect(DB)




def save_trade(signal):

    conn = connect()

    cur = conn.cursor()


    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        time TEXT,

        direction TEXT,

        entry REAL,

        sl REAL,

        tp REAL,

        score INTEGER,

        result TEXT

    )
    """)



    cur.execute("""
    INSERT INTO trades
    (
    time,
    direction,
    entry,
    sl,
    tp,
    score,
    result
    )

    VALUES(?,?,?,?,?,?,?)

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
    ),

    "ACTIVE"

    ))


    conn.commit()

    conn.close()






def get_trades():

    conn = connect()

    cur = conn.cursor()


    cur.execute(
        "SELECT * FROM trades"
    )


    data = cur.fetchall()


    conn.close()


    return data





def update_result(
    trade_id,
    result
):

    conn = connect()

    cur = conn.cursor()


    cur.execute(
"""
UPDATE trades

SET result=?

WHERE id=?

""",

(
result,
trade_id
)

)


    conn.commit()

    conn.close()
