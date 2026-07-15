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
        profit REAL DEFAULT 0,
        user_id INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE,
        setting_value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    default_settings = [
        ('daily_signal_limit', '5'),
        ('referral_bonus', '1'),
        ('referral_threshold', '5'),
        ('rr_ratio', '2'),
        ('default_timeframe', '1h'),
        ('bot_locked', 'false'),
        ('signal_enabled', 'true'),
        ('channel_locked', 'false')
    ]

    for key, value in default_settings:
        cursor.execute(
            "INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)",
            (key, value)
        )

    conn.commit()
    conn.close()

def get_setting(key):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT setting_value FROM bot_settings WHERE setting_key=?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def update_setting(key, value):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE bot_settings SET setting_value=?, updated_at=CURRENT_TIMESTAMP WHERE setting_key=?",
        (value, key)
    )
    conn.commit()
    conn.close()
    return True

def get_all_settings():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT setting_key, setting_value FROM bot_settings")
    results = cursor.fetchall()
    conn.close()
    return {key: value for key, value in results}

def save_trade(signal, user_id=0):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO trades (time, direction, entry, sl, tp, score, result, user_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        signal["direction"],
        signal["entry"],
        signal["sl"],
        signal["tp"],
        signal.get("score", 0),
        "OPEN",
        user_id
    ))

    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trade_id

def update_result(trade_id, result):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE trades SET result=? WHERE id=?",
        (result, trade_id)
    )

    conn.commit()
    conn.close()

def get_user_trades(user_id=0):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT direction, entry, sl, tp, result, time FROM trades WHERE user_id=? OR user_id=0 ORDER BY id DESC LIMIT 10",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    result = []
    for t in rows:
        result.append({
            'direction': t[0],
            'entry': t[1],
            'sl': t[2],
            'tp': t[3],
            'result': t[4] if t[4] else 'در انتظار',
            'time': t[5]
        })
    return result

def get_statistics():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT result FROM trades")
    rows = cursor.fetchall()
    conn.close()

    total = len(rows)
    wins = sum(1 for r in rows if r[0] == "TP")
    losses = sum(1 for r in rows if r[0] == "SL")

    winrate = round((wins / total) * 100, 2) if total > 0 else 0

    return {
        'total': total,
        'wins': wins,
        'losses': losses,
        'winrate': winrate
    }
