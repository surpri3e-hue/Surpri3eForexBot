import sqlite3
from datetime import datetime


DB = "logs.db"



def connect():

    return sqlite3.connect(DB)





def create_logs():

    conn = connect()

    cur = conn.cursor()


    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        time TEXT,

        action TEXT

    )
    """)


    conn.commit()

    conn.close()





def add_log(action):

    conn = connect()

    cur = conn.cursor()


    cur.execute("""
    INSERT INTO logs
    (
        time,
        action
    )

    VALUES (?,?)

    """,

    (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        ),

        action
    ))


    conn.commit()

    conn.close()





def get_logs(limit=10):

    conn = connect()

    cur = conn.cursor()


    cur.execute("""
    SELECT time, action
    FROM logs
    ORDER BY id DESC
    LIMIT ?
    """,

    (
        limit,
    ))


    rows = cur.fetchall()


    conn.close()


    return rows
