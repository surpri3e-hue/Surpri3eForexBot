import sqlite3
from datetime import datetime, timedelta

DB_NAME = "trades.db"


def connect():
    return sqlite3.connect(DB_NAME)


def _column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


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
        style TEXT DEFAULT 'ICT',
        strength TEXT DEFAULT 'NORMAL'
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
        style TEXT DEFAULT 'surpri3e',
        is_vip INTEGER DEFAULT 0,
        referral_count INTEGER DEFAULT 0,
        referred_by INTEGER DEFAULT 0,
        daily_signal_limit INTEGER DEFAULT 5,
        signals_used_today INTEGER DEFAULT 0,
        last_signal_reset TEXT,
        rr_ratio REAL DEFAULT 2,
        last_signal_at TEXT,
        last_signal_timeframe TEXT
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

    # ===== جدول تنظیمات استراتژی‌ها (پارامترهای هر استراتژی، مثل سخت‌گیری) =====
    # کلید به‌صورت "strategy_id.param_name" ذخیره می‌شه، مثلاً "surpri3e.depth"
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS strategy_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE,
        setting_value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ===== migration برای دیتابیس‌های قدیمی‌تر که ستون‌های جدید رو ندارن =====
    if not _column_exists(cursor, "users", "rr_ratio"):
        cursor.execute("ALTER TABLE users ADD COLUMN rr_ratio REAL DEFAULT 2")

    if not _column_exists(cursor, "users", "last_signal_at"):
        cursor.execute("ALTER TABLE users ADD COLUMN last_signal_at TEXT")

    if not _column_exists(cursor, "users", "last_signal_timeframe"):
        cursor.execute("ALTER TABLE users ADD COLUMN last_signal_timeframe TEXT")

    if not _column_exists(cursor, "trades", "strength"):
        cursor.execute("ALTER TABLE trades ADD COLUMN strength TEXT DEFAULT 'NORMAL'")

    # ===== migration: کاربرانی که از قبل با style قدیمی (ICT/SMC) ثبت شدن =====
    # چون signals.py دیگه فقط SURPRI3E رو می‌شناسه، این کاربرا باید بروزرسانی بشن
    # وگرنه create_signal همیشه None برمی‌گردونه (باگی که باعث "سیگنال نمی‌ده" می‌شد)
    cursor.execute("UPDATE users SET style='surpri3e' WHERE style IS NULL OR style IN ('ICT', 'SMC')")

    # ===== تنظیمات پیش‌فرض =====
    default_settings = [
        ('daily_signal_limit', '5'),
        ('referral_bonus', '1'),
        ('referral_threshold', '5'),
        ('rr_ratio', '2'),  # این فقط RR پیش‌فرض برای کاربر تازه‌واردـه
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


# ============ تنظیمات (Global) ============
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


# ============ تنظیمات استراتژی‌ها (پارامترهای قابل تغییر هر استراتژی) ============
def get_strategy_setting(strategy_id, param_name, default=None):
    """
    مقدار یک پارامتر مشخص از یک استراتژی رو می‌خونه.
    اگه هنوز تو دیتابیس ذخیره نشده باشه، مقدار default (که معمولاً از
    خود فایل استراتژی میاد) رو برمی‌گردونه.
    """
    key = f"{strategy_id}.{param_name}"
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT setting_value FROM strategy_settings WHERE setting_key=?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default


def set_strategy_setting(strategy_id, param_name, value):
    """مقدار یک پارامتر استراتژی رو ذخیره/به‌روزرسانی می‌کنه."""
    key = f"{strategy_id}.{param_name}"
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO strategy_settings (setting_key, setting_value) VALUES (?, ?) "
        "ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value, updated_at=CURRENT_TIMESTAMP",
        (key, str(value))
    )
    conn.commit()
    conn.close()


def get_all_strategy_settings(strategy_id):
    """همه‌ی پارامترهای ذخیره‌شده‌ی یک استراتژی رو برمی‌گردونه (dict: param_name -> value)."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT setting_key, setting_value FROM strategy_settings WHERE setting_key LIKE ?", (f"{strategy_id}.%",))
    results = cursor.fetchall()
    conn.close()
    prefix_len = len(strategy_id) + 1
    return {key[prefix_len:]: value for key, value in results}


def reset_strategy_settings(strategy_id):
    """همه‌ی پارامترهای ذخیره‌شده‌ی یک استراتژی رو پاک می‌کنه (برمی‌گرده به مقادیر پیش‌فرض کد)."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM strategy_settings WHERE setting_key LIKE ?", (f"{strategy_id}.%",))
    conn.commit()
    conn.close()


# ============ کاربران ============
def user_exists(user_id):
    """چک می‌کنه کاربر قبلاً تو دیتابیس ثبت شده یا نه (برای تشخیص کاربر جدید/قدیمی در /start)."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def add_user(user_id, username=None, first_name=None, last_name=None, lang='fa'):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE users SET lang=? WHERE id=?", (lang, user_id))
        conn.commit()
        conn.close()
        return

    default_rr = float(get_setting('rr_ratio') or '2')

    cursor.execute("""
    INSERT INTO users (id, username, first_name, last_name, joined_at, last_active, lang, daily_signal_limit, rr_ratio)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        first_name,
        last_name,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        lang,
        5,
        default_rr
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
    # پیش‌فرض SURPRI3E است، نه ICT قدیمی که دیگر signals.py آن را نمی‌شناسد
    return result[0] if result and result[0] else 'surpri3e'


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


# ============ RR اختصاصی هر کاربر (جدید) ============
def set_user_rr(user_id, rr_value):
    """نسبت RR مخصوص همین کاربر رو ذخیره می‌کنه، نه سراسری."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET rr_ratio=? WHERE id=?", (float(rr_value), user_id))
    conn.commit()
    conn.close()


def get_user_rr(user_id):
    """RR اختصاصی کاربر رو برمی‌گردونه؛ اگه نبود، مقدار پیش‌فرض سراسری."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT rr_ratio FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0]:
        return float(result[0])
    return float(get_setting('rr_ratio') or '2')


# ============ Cooldown سیگنال بر اساس تایم‌فریم ============
# فاصله‌ی مجاز بین دو درخواست سیگنال = طول خود کندل، تا کندل هنوز
# نبسته دوباره تحلیل نشه و همون سیگنال متناقض چند بار نیاد.
TIMEFRAME_SECONDS = {
    "1min": 60,
    "5min": 5 * 60,
    "15min": 15 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "1d": 24 * 60 * 60,
}


def check_signal_cooldown(user_id, timeframe):
    """
    بررسی می‌کنه آیا کاربر مجاز به درخواست سیگنال جدیده یا باید صبر کنه.

    خروجی: (allowed: bool, seconds_left: int)
        allowed=True  -> می‌تونه سیگنال بگیره
        allowed=False -> باید seconds_left ثانیه‌ی دیگه صبر کنه
    """
    import os
    ADMIN_ID = int(os.getenv("ADMIN_ID", 816822644))
    if user_id == ADMIN_ID:
        return True, 0

    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT last_signal_at, last_signal_timeframe FROM users WHERE id=?",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()

    if not result or not result[0]:
        return True, 0

    last_signal_at_str, last_tf = result
    try:
        last_signal_at = datetime.strptime(last_signal_at_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return True, 0

    cooldown = TIMEFRAME_SECONDS.get(timeframe, 5 * 60)
    elapsed = (datetime.now() - last_signal_at).total_seconds()

    if elapsed >= cooldown:
        return True, 0

    return False, int(cooldown - elapsed)


def record_signal_time(user_id, timeframe):
    """بعد از تولید موفق سیگنال صدا زده می‌شه تا زمان آخرین سیگنال ثبت بشه."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_signal_at=?, last_signal_timeframe=? WHERE id=?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), timeframe, user_id)
    )
    conn.commit()
    conn.close()


# ============ رفرال ============
def get_referral_link(user_id):
    import os
    bot_username = os.getenv("BOT_USERNAME", "Surpri3eFXbot")
    return f"https://t.me/{bot_username}?start=ref_{user_id}"


def process_referral(user_id, referrer_id):
    if user_id == referrer_id:
        return False

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT referred_by FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()

    if result and result[0] != 0:
        conn.close()
        return False

    cursor.execute("UPDATE users SET referred_by=? WHERE id=?", (referrer_id, user_id))
    cursor.execute("UPDATE users SET referral_count = referral_count + 1 WHERE id=?", (referrer_id,))
    conn.commit()
    conn.close()

    check_referral_bonus(referrer_id)
    return True


def check_referral_bonus(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT referral_count, daily_signal_limit FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()

    if result:
        referral_count = result[0]
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


# ============ معاملات ============
def save_trade(signal, user_id=0, style='ICT', strength='NORMAL'):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO trades (time, direction, entry, sl, tp, result, user_id, style, strength)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        signal["direction"],
        signal["entry"],
        signal["sl"],
        signal["tp"],
        "OPEN",
        user_id,
        style,
        strength
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
            'style': t[6] if len(t) > 6 else 'ICT'
        })
    return result


def get_statistics():
    """
    آمار کلی (global) - فقط بر اساس معاملاتی که واقعاً TP یا SL خوردن.
    معاملات OPEN (که هنوز نتیجه‌شون مشخص نشده) در محاسبه‌ی winrate
    لحاظ نمی‌شن، چون هنوز برد/باخت نبودنشون معلوم نیست.
    """
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT result FROM trades WHERE result IN ('TP', 'SL')")
    rows = cursor.fetchall()
    conn.close()

    total = len(rows)  # فقط معاملات بسته‌شده (TP یا SL)
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


def _winrate_for_rows(rows):
    """کمکی: از لیست result ها فقط TP/SL رو حساب می‌کنه و winrate می‌سازه."""
    closed = [r[0] for r in rows if r[0] in ('TP', 'SL')]
    total = len(closed)
    wins = sum(1 for r in closed if r == 'TP')
    losses = sum(1 for r in closed if r == 'SL')
    winrate = round((wins / total) * 100, 2) if total > 0 else 0
    return {'total': total, 'wins': wins, 'losses': losses, 'winrate': winrate}


def get_user_winrate_stats(user_id):
    """
    آمار وین‌ریت شخصی یک کاربر در سه بازه: کل، ۷ روز اخیر، ۳۰ روز اخیر.
    فقط معاملات همون کاربر (user_id) رو در نظر می‌گیره - نه معاملات بقیه.
    فقط معاملاتی که واقعاً TP یا SL خوردن حساب می‌شن (نه OPEN).
    """
    conn = connect()
    cursor = conn.cursor()

    # ===== کل تاریخچه =====
    cursor.execute("SELECT result FROM trades WHERE user_id=?", (user_id,))
    all_rows = cursor.fetchall()

    # ===== ۷ روز اخیر =====
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M')
    cursor.execute(
        "SELECT result FROM trades WHERE user_id=? AND time >= ?",
        (user_id, week_ago)
    )
    week_rows = cursor.fetchall()

    # ===== ۳۰ روز اخیر =====
    month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M')
    cursor.execute(
        "SELECT result FROM trades WHERE user_id=? AND time >= ?",
        (user_id, month_ago)
    )
    month_rows = cursor.fetchall()

    conn.close()

    return {
        'all_time': _winrate_for_rows(all_rows),
        'weekly': _winrate_for_rows(week_rows),
        'monthly': _winrate_for_rows(month_rows),
    }
