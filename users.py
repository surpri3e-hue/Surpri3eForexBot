import sqlite3
from datetime import datetime


DB = "users.db"



def connect():
    return sqlite3.connect(DB)



def create_users_table():

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        telegram_id INTEGER UNIQUE,

        join_date TEXT,

        last_active TEXT,

        status TEXT DEFAULT 'active'

    )
    """)

    conn.commit()
    conn.close()





def add_user(user_id):

    conn = connect()
    cur = conn.cursor()


    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M"
    )


    cur.execute("""
    INSERT OR IGNORE INTO users
    (
        telegram_id,
        join_date,
        last_active
    )

    VALUES (?,?,?)
    """,
    (
        user_id,
        now,
        now
    ))


    conn.commit()
    conn.close()





def update_activity(user_id):

    conn = connect()
    cur = conn.cursor()


    cur.execute("""
    UPDATE users
    SET last_active=?
    WHERE telegram_id=?
    """,
    (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        user_id
    ))


    conn.commit()
    conn.close()





def get_users_count():

    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM users"
    )

    result = cur.fetchone()[0]

    conn.close()

    return result
