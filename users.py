# users.py
import sqlite3
from datetime import datetime
import os

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
        lang TEXT DEFAULT 'fa',
        style TEXT DEFAULT 'ZIGZAG',
        is_vip INTEGER DEFAULT 0,
        referral_count INTEGER DEFAULT 0,
        referred_by INTEGER DEFAULT 0,
        daily_signal_limit INTEGER DEFAULT 5,
        signals_used_today INTEGER DEFAULT 0,
        last_signal_reset TEXT,
        rr_ratio REAL DEFAULT 2.0
    )
    """)

    conn.commit()
    conn.close()

def add_user(user_id, username=None, first_name=None, last_name=None, lang='fa'):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if cursor.fetchone():
        # به‌روزرسانی زبان و فعالیت
        cursor.execute(
            "UPDATE users SET lang=?, last_active=? WHERE id=?",
            (lang, datetime.now().strftime("%Y-%m-%d %H:%M"), user_id)
        )
        conn.commit()
        conn.close()
        return

    cursor.execute("""
    INSERT INTO users (
        id, username, first_name, last_name, joined_at, last_active, lang, daily_signal_limit
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        first_name,
        last_name,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        lang,
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
    cursor.execute("""
        SELECT id, last_active, is_vip, referral_count, lang, style 
        FROM users ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        'id': r[0],
        'last_active': r[1],
        'is_vip': bool(r[2]),
        'referral_count': r[3],
        'lang': r[4] if len(r) > 4 else 'fa',
        'style': r[5] if len(r) > 5 else 'ZIGZAG'
    } for r in rows]

def get_user_lang(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'fa'

def get_user_style(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT style FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'ZIGZAG'

def set_user_style(user_id, style):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET style=? WHERE id=?", (style, user_id))
    conn.commit()
    conn.close()

def is_user_vip(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT is_vip FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return bool(result[0]) if result else False

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

# ============ RR اختصاصی کاربر ============
def set_user_rr(user_id, rr):
    """تنظیم RR اختصاصی برای هر کاربر"""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET rr_ratio=? WHERE id=?", (rr, user_id))
    conn.commit()
    conn.close()

def get_user_rr(user_id):
    """دریافت RR اختصاصی کاربر"""
    from database import get_setting
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT rr_ratio FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0] is not None:
        return float(result[0])
    return float(get_setting('rr_ratio') or '2')

# ============ سیستم رفرال ============
def get_referral_link(user_id):
    bot_username = os.getenv("BOT_USERNAME", "Surpri3eFXbot")
    return f"https://t.me/{bot_username}?start=ref_{user_id}"

def process_referral(user_id, referrer_id):
    if user_id == referrer_id:
        return False

    conn = connect()
    cursor = conn.cursor()

    # بررسی اینکه کاربر قبلاً توسط کسی معرفی نشده
    cursor.execute("SELECT referred_by FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()

    if result and result[0] != 0:
        conn.close()
        return False

    # ثبت رفرال
    cursor.execute("UPDATE users SET referred_by=? WHERE id=?", (referrer_id, user_id))
    cursor.execute("UPDATE users SET referral_count = referral_count + 1 WHERE id=?", (referrer_id,))

    conn.commit()
    conn.close()

    # اعمال پاداش
    check_referral_bonus(referrer_id)
    return True

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
            new_limit = 5 + extra_signals
            cursor.execute(
                "UPDATE users SET daily_signal_limit = ? WHERE id=?",
                (new_limit, user_id)
            )
            conn.commit()

    conn.close()

# ============ مدیریت سیگنال روزانه ============
def reset_daily_signals():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET signals_used_today = 0, last_signal_reset = CURRENT_TIMESTAMP")
    conn.commit()
    conn.close()

def get_user_signals_left(user_id):
    import os
    ADMIN_ID = int(os.getenv("ADMIN_ID", 816822644))

    if user_id == ADMIN_ID:
        return 999

    if is_user_vip(user_id):
        return 999

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
    import os
    ADMIN_ID = int(os.getenv("ADMIN_ID", 816822644))

    if user_id == ADMIN_ID:
        return True

    if is_user_vip(user_id):
        return True

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET signals_used_today = signals_used_today + 1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return True

def get_active_users_today():
    conn = connect()
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) FROM users WHERE date(last_active)=?", (today,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_user_detail(user_id):
    """دریافت اطلاعات کامل یک کاربر"""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, first_name, last_name, joined_at, last_active,
               is_vip, referral_count, daily_signal_limit, signals_used_today,
               lang, style, rr_ratio
        FROM users WHERE id=?
    """, (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            'id': result[0],
            'username': result[1],
            'first_name': result[2],
            'last_name': result[3],
            'joined_at': result[4],
            'last_active': result[5],
            'is_vip': bool(result[6]),
            'referral_count': result[7],
            'daily_signal_limit': result[8],
            'signals_used_today': result[9],
            'lang': result[10] if len(result) > 10 else 'fa',
            'style': result[11] if len(result) > 11 else 'ZIGZAG',
            'rr_ratio': result[12] if len(result) > 12 else 2.0
        }
    return None
