import sqlite3
from datetime import datetime

DB_NAME = "users.db"

def connect():
    return sqlite3.connect(DB_NAME)

def create_users_table():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        joined_at TEXT,
        last_active TEXT,
        is_vip INTEGER DEFAULT 0,
        referral_count INTEGER DEFAULT 0,
        referred_by INTEGER DEFAULT 0,
        daily_signal_limit INTEGER DEFAULT 5,
        signals_used_today INTEGER DEFAULT 0,
        last_signal_reset TEXT
    )
    """)

    conn.commit()
    conn.close()

def add_user(user_id, username=None, first_name=None, last_name=None):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if cursor.fetchone():
        conn.close()
        return

    cursor.execute("""
    INSERT INTO users (id, username, first_name, last_name, joined_at, last_active, daily_signal_limit)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        first_name,
        last_name,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        5
    ))

    conn.commit()
    conn.close()

def update_activity(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_active=? WHERE id=?",
        (datetime.now().strftime("%Y-%m-%d %H:%M"), user_id)
    )
    conn.commit()
    conn.close()

def get_users_count():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_all_users():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, last_active, is_vip, referral_count FROM users ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'last_active': r[1], 'is_vip': bool(r[2]), 'referral_count': r[3]} for r in rows]

def get_user_detail(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, first_name, joined_at, last_active, is_vip, referral_count, daily_signal_limit, signals_used_today "
        "FROM users WHERE id=?",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            'id': result[0],
            'username': result[1],
            'first_name': result[2],
            'joined_at': result[3],
            'last_active': result[4],
            'is_vip': bool(result[5]),
            'referral_count': result[6],
            'daily_signal_limit': result[7],
            'signals_used_today': result[8]
        }
    return None

def get_active_users_today():
    conn = connect()
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) FROM users WHERE date(last_active)=?", (today,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def add_referral(user_id, referrer_id):
    from database import get_setting
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET referral_count = referral_count + 1 WHERE id=?", (referrer_id,))
    cursor.execute("UPDATE users SET referred_by=? WHERE id=?", (referrer_id, user_id))

    conn.commit()
    conn.close()
    
    # ===== اعمال پاداش =====
    check_referral_bonus(referrer_id)

def check_referral_bonus(user_id):
    from database import get_setting
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT referral_count, daily_signal_limit FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()

    if result:
        referral_count = result[0]
        current_limit = result[1]
        threshold = int(get_setting('referral_threshold') or '5')
        bonus = int(get_setting('referral_bonus') or '1')

        if referral_count > 0:
            extra_signals = (referral_count // threshold) * bonus
            new_limit = 5 + extra_signals  # مقدار پایه 5
            cursor.execute(
                "UPDATE users SET daily_signal_limit = ? WHERE id=?",
                (new_limit, user_id)
            )
            conn.commit()
            return new_limit

    conn.close()
    return None

def reset_daily_signals():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET signals_used_today = 0, last_signal_reset = CURRENT_TIMESTAMP")
    conn.commit()
    conn.close()

def get_user_signals_left(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT daily_signal_limit, signals_used_today FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        limit, used = result
        return max(0, limit - used)
    return 0

def use_signal(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET signals_used_today = signals_used_today + 1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

def set_user_vip(user_id, is_vip=True):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_vip=? WHERE id=?", (1 if is_vip else 0, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
