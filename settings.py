import sqlite3


DB_NAME = "settings.db"



def connect():

    return sqlite3.connect(DB_NAME)





def create_settings():

    conn = connect()
    cur = conn.cursor()


    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (

        key TEXT PRIMARY KEY,

        value TEXT

    )
    """)


    default_settings = [

        ("channel_lock", "OFF"),

        ("channel_id", ""),

        ("bot_status", "ON"),

        ("signal_status", "ON"),

        ("minimum_score", "70"),

        ("ai_mode", "NORMAL"),

        ("fvg_filter", "ON"),

        ("liquidity_filter", "ON"),

        ("bos_filter", "ON"),

        ("send_chart", "OFF"),

        ("maintenance", "OFF")

    ]



    for key, value in default_settings:

        cur.execute(
            """
            INSERT OR IGNORE INTO settings
            (key,value)

            VALUES (?,?)
            """,

            (
                key,
                value
            )

        )


    conn.commit()

    conn.close()





def get_setting(key):

    conn = connect()
    cur = conn.cursor()


    cur.execute(
        """
        SELECT value
        FROM settings
        WHERE key=?
        """,

        (
            key,
        )
    )


    result = cur.fetchone()

    conn.close()



    if result:

        return result[0]


    return None





def set_setting(key, value):

    conn = connect()
    cur = conn.cursor()


    cur.execute(
        """
        INSERT OR REPLACE INTO settings

        (key,value)

        VALUES (?,?)

        """,

        (
            key,
            str(value)
        )

    )


    conn.commit()

    conn.close()





def init_settings():

    create_settings()
