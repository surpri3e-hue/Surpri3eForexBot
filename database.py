# database.py
import sqlite3
from datetime import datetime, timedelta

DB_NAME = "trades.db"

def connect():
    return sqlite3.connect(DB_NAME)

def create_database():
    conn = connect()
    cursor = conn.cursor()

    # ===== جدول معاملات =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT,
        direction TEXT,
        entry REAL,
        sl REAL,
        tp REAL,
        result TEXT DEFAULT 'OPEN',
        user_id INTEGER DEFAULT 0,
        style TEXT DEFAULT 'ZIGZAG'
    )
    """)

    # ===== جدول کاربران =====
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

    # ===== جدول تنظیمات ربات =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE,
        setting_value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ===== تنظیمات پیش‌فرض =====
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

# ============ تنظیمات ============
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

# ============ کاربران ============
def add_user(user_id, username=None, first_name=None, last_name=None, lang='fa'):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE users SET lang=?, last_active=? WHERE id=?", 
                       (lang, datetime.now().strftime("%Y-%m-%d %H:%M"), user_id))
        conn.commit()
        conn.close()
        return

    cursor.execute("""
    INSERT INTO users (id, username, first_name, last_name, joined_at, last_active, lang, daily_signal_limit)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
    cursor.execute("SELECT id, last_active, is_vip, referral_count, lang, style FROM users ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'last_active': r[1], 'is_vip': bool(r[2]), 'referral_count': r[3], 'lang': r[4], 'style': r[5]} for r in rows]

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
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT rr_ratio FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0] is not None:
        return float(result[0])
    return float(get_setting('rr_ratio') or '2')

# ============ آمار هفتگی و ماهانه ============
def get_weekly_stats():
    """دریافت وین‌ریت هفته جاری"""
    conn = connect()
    cursor = conn.cursor()
    
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week_str = start_of_week.strftime('%Y-%m-%d')
    
    cursor.execute(
        "SELECT result FROM trades WHERE date(time) >= ?",
        (start_of_week_str,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    total = len(rows)
    wins = sum(1 for r in rows if r[0] == "TP")
    winrate = round((wins / total) * 100, 2) if total > 0 else 0
    return {'total': total, 'wins': wins, 'winrate': winrate}

def get_monthly_stats():
    """دریافت وین‌ریت ماه جاری"""
    conn = connect()
    cursor = conn.cursor()
    
    today = datetime.now()
    start_of_month = today.replace(day=1)
    start_of_month_str = start_of_month.strftime('%Y-%m-%d')
    
    cursor.execute(
        "SELECT result FROM trades WHERE date(time) >= ?",
        (start_of_month_str,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    total = len(rows)
    wins = sum(1 for r in rows if r[0] == "TP")
    winrate = round((wins / total) * 100, 2) if total > 0 else 0
    return {'total': total, 'wins': wins, 'winrate': winrate}

# ============ معاملات ============
def save_trade(signal, user_id=0, style='ZIGZAG'):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO trades (time, direction, entry, sl, tp, result, user_id, style)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        signal["direction"],
        signal["entry"],
        signal["sl"],
        signal["tp"],
        "OPEN",
        user_id,
        style
    ))

    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trade_id

def update_result(trade_id, result):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE trades SET result=? WHERE id=?", (result, trade_id))
    conn.commit()
    conn.close()

def get_user_trades(user_id=0):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT direction, entry, sl, tp, result, time, style FROM trades WHERE user_id=? OR user_id=0 ORDER BY id DESC LIMIT 10",
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
            'time': t[5],
            'style': t[6] if len(t) > 6 else 'ZIGZAG'
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

def get_today_stats():
    conn = connect()
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')

    cursor.execute("SELECT COUNT(*) FROM trades WHERE date(time)=?", (today,))
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM trades WHERE date(time)=? AND result='TP'", (today,))
    tp = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM trades WHERE date(time)=? AND result='SL'", (today,))
    sl = cursor.fetchone()[0]

    conn.close()
    return {'signals_used': total, 'tp_count': tp, 'sl_count': sl}

def get_active_users_today():
    conn = connect()
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) FROM users WHERE date(last_active)=?", (today,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0
