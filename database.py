# ============================================================
# 📌 لایه‌ی اتصال دیتابیس - پشتیبانی از PostgreSQL (Neon) و SQLite
#
# ⚠️ چرا این تغییر لازم بود: قبلاً دیتابیس SQLite (فایل trades.db) بود
# که مستقیم روی دیسک سرور (Railway) ذخیره می‌شد. Railway فایل‌سیستمش
# موقتیه - هر بار که کد جدید دیپلوی می‌شد (push به گیت‌هاب)، یک کانتینر
# کاملاً تازه ساخته می‌شد و هر فایلی که قبلاً روی دیسک بود (شامل خودِ
# دیتابیس) از بین می‌رفت. این باعث می‌شد کاربران، تاریخچه‌ی معاملات،
# VIP ها و همه‌چیز بعد از هر آپدیت کد صفر بشه.
#
# ✅ راه‌حل: دیتابیس به یک سرویس PostgreSQL ابری (Neon) منتقل شد که کاملاً
# جدا از سرور کد زندگی می‌کنه - پس دیپلوی مجدد کد هیچ اثری روی دیتای
# ذخیره‌شده نداره.
#
# نحوه‌ی تنظیم: متغیر محیطی DATABASE_URL باید روی آدرس اتصال Neon تنظیم
# بشه (تو پنل Railway، بخش Variables). اگه این متغیر تنظیم نشده باشه
# (مثلاً موقع تست محلی روی سیستم شخصی)، کد به‌صورت خودکار به یک فایل
# SQLite محلی (trades.db) برمی‌گرده - برای این‌که تست لوکال بدون نیاز
# به دیتابیس واقعی هم امکان‌پذیر باشه.
#
# تمام کد بقیه‌ی این فایل با سینتکس "?" برای پارامترها نوشته شده
# (استاندارد SQLite) - شیء Cursor سفارشی زیر، خودکار "?" رو به "%s"
# (سینتکس PostgreSQL) تبدیل می‌کنه، پس نیازی به تغییر ۸۰+ کوئری موجود
# در این فایل نبود و ریسک خطای تایپی در این مهاجرت بزرگ به حداقل رسید.
#
# ⚠️ رفع باگ کندی بعد از اتصال به Neon: قبلاً هر بار که connect() صدا
# زده می‌شد (که برای هر عملیات دیتابیس، حتی خوندن یک تنظیم ساده، اتفاق
# می‌افته - ده‌ها بار در هر تعامل کاربر با ربات)، یک اتصال کاملاً تازه
# TCP+TLS به سرور Neon (که روی اینترنت است، نه لوکال) باز می‌شد. برخلاف
# SQLite (که "اتصال" بهش تقریباً هزینه‌ی صفر داره چون فقط یک فایل محلیه)،
# باز کردن هر اتصال جدید PostgreSQL با SSL می‌تونه صدها میلی‌ثانیه طول
# بکشه - و چون این هزینه برای هر کوئری تکرار می‌شد، در مجموع باعث کندی
# محسوس (که در استفاده‌ی واقعی می‌تونست به چند ثانیه یا بیشتر برسه) می‌شد.
#
# ✅ راه‌حل: یک Connection Pool واقعی (psycopg2.pool) که تعدادی اتصال از
# قبل باز نگه می‌داره و بین عملیات‌های مختلف بازیافت می‌کنه. تابع connect()
# دیگه اتصال تازه نمی‌سازه - یکی از اتصالات آماده‌ی pool رو برمی‌داره؛ و
# close() دیگه واقعاً اتصال رو قطع نمی‌کنه، فقط به pool برش می‌گردونه تا
# دفعه‌ی بعد دوباره استفاده بشه. این تغییر در همین یک تابع مرکزی انجام
# شده - نیازی به تغییر ۵۰+ نقطه‌ای که connect() رو صدا می‌زنن نبود.
# ============================================================
import os
from datetime import datetime, timedelta

DB_NAME = "trades.db"
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extensions
    from psycopg2.pool import ThreadedConnectionPool
    # ===== psycopg2 به‌طور پیش‌فرض هر INTEGER بزرگ رو به‌درستی می‌خونه، =====
    # ===== ولی برای اطمینان از سازگاری کامل با کدی که REAL/TEXT خام SQLite =====
    # ===== انتظار داره، از دیکود پیش‌فرض استفاده می‌کنیم (تغییری لازم نیست) =====

    # ===== ThreadedConnectionPool چون ربات چندریسمانی (thread pool برای =====
    # ===== سیگنال‌گیری/auto_tracker) داره - این pool thread-safe است. =====
    # minconn=2: همیشه حداقل ۲ اتصال آماده نگه می‌داره (بدون تأخیر اولین درخواست)
    # maxconn=20: سقف اتصالات هم‌زمان - کافی برای بار متوسط بدون اتلاف منابع Neon
    _pg_pool = ThreadedConnectionPool(minconn=2, maxconn=20, dsn=DATABASE_URL)
else:
    import sqlite3


class _CompatCursor:
    """
    Cursor سفارشی که پشت صحنه بین سینتکس SQLite ("?") و PostgreSQL ("%s")
    ترجمه می‌کنه. بقیه‌ی این فایل همیشه با "?" نوشته می‌شه (چون اکثر کد
    قبلاً بر این اساس نوشته شده بود)؛ این کلاس تبدیل رو خودکار انجام می‌ده.
    """
    def __init__(self, real_cursor):
        self._cursor = real_cursor

    def execute(self, query, params=None):
        if USE_POSTGRES and params is not None:
            # ===== تبدیل "?" به "%s" - فقط علامت سؤال بیرون از رشته‌های متنی =====
            query = query.replace("?", "%s")
        if params is not None:
            return self._cursor.execute(query, params)
        return self._cursor.execute(query)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        if USE_POSTGRES:
            # ===== psycopg2 مثل sqlite3 مستقیم lastrowid نداره - =====
            # ===== کوئری‌هایی که به این نیاز دارن از RETURNING id استفاده می‌کنن =====
            return getattr(self._cursor, '_pg_lastrowid', None)
        return self._cursor.lastrowid


class _CompatConnection:
    """
    Connection سفارشی که هم روی psycopg2 (PostgreSQL) و هم sqlite3 کار
    می‌کنه، با یک واسط یکسان (connect().cursor(), .commit(), .close()).

    برای PostgreSQL: این اتصال از یک Connection Pool گرفته شده - پس
    close() به‌جای قطع واقعی اتصال، فقط اونو به pool برمی‌گردونه تا
    درخواست بعدی بتونه دوباره ازش استفاده کنه (بدون هزینه‌ی باز کردن
    اتصال تازه).
    """
    def __init__(self, real_conn):
        self._conn = real_conn

    def cursor(self):
        return _CompatCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def close(self):
        if USE_POSTGRES:
            # ===== قبل از برگردوندن به pool، مطمئن می‌شیم تراکنش باز/نیمه‌کاره =====
            # ===== نمونده - وگرنه درخواست بعدی که همین اتصال رو می‌گیره، =====
            # ===== ممکنه با یک تراکنش قدیمی/معلق روبه‌رو بشه. =====
            try:
                if not self._conn.closed and self._conn.status != psycopg2.extensions.STATUS_READY:
                    self._conn.rollback()
            except Exception:
                pass
            _pg_pool.putconn(self._conn)
        else:
            self._conn.close()


def connect():
    if USE_POSTGRES:
        # ===== به‌جای ساختن اتصال تازه، یکی از اتصالات آماده‌ی pool رو می‌گیریم =====
        raw_conn = _pg_pool.getconn()
        return _CompatConnection(raw_conn)
    return _CompatConnection(sqlite3.connect(DB_NAME))


def _column_exists(cursor, table, column):
    """
    چک می‌کنه یک ستون تو یک جدول وجود داره یا نه - سازگار با هر دو
    دیتابیس (SQLite از PRAGMA استفاده می‌کنه، PostgreSQL از information_schema).
    """
    if USE_POSTGRES:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name=? AND column_name=?",
            (table, column)
        )
        return cursor.fetchone() is not None
    else:
        cursor.execute(f"PRAGMA table_info({table})")
        return any(row[1] == column for row in cursor.fetchall())


def _pk_clause():
    """بند PRIMARY KEY خودافزا - نحوه‌ی نوشتنش بین دو دیتابیس فرق داره."""
    return "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def _insert_ignore(table, columns, conn, cursor, values):
    """
    معادل INSERT OR IGNORE (سینتکس SQLite) که در PostgreSQL به‌صورت
    ON CONFLICT DO NOTHING نوشته می‌شه. برای درج تنظیمات پیش‌فرض استفاده
    می‌شه (اگه از قبل وجود داشته باشن، نادیده گرفته می‌شن).
    """
    placeholders = ", ".join(["?"] * len(columns))
    col_names = ", ".join(columns)
    if USE_POSTGRES:
        conflict_col = columns[0]  # اولین ستون معمولاً UNIQUE/PK هست (setting_key)
        query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT ({conflict_col}) DO NOTHING"
    else:
        query = f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})"
    cursor.execute(query, values)


def _insert_returning_id(query, params, cursor):
    """
    اجرای یک INSERT و برگردوندن id ردیف تازه‌ساخته‌شده - سازگار با هر دو
    دیتابیس. SQLite از cursor.lastrowid پشتیبانی می‌کنه؛ PostgreSQL نیاز
    به افزودن "RETURNING id" به کوئری و fetchone دارد.

    query باید یک INSERT ... VALUES (...) باشه بدون RETURNING در انتهاش -
    این تابع خودش RETURNING id رو (فقط برای PostgreSQL) اضافه می‌کنه.
    """
    if USE_POSTGRES:
        query_with_returning = query.rstrip().rstrip(';') + " RETURNING id"
        cursor.execute(query_with_returning, params)
        return cursor.fetchone()[0]
    else:
        cursor.execute(query, params)
        return cursor.lastrowid


def create_database():
    conn = connect()
    cursor = conn.cursor()
    pk = _pk_clause()

    # ===== جدول معاملات =====
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS trades (
        id {pk},
        time TEXT,
        direction TEXT,
        entry REAL,
        sl REAL,
        tp REAL,
        result TEXT DEFAULT 'OPEN',
        user_id INTEGER DEFAULT 0,
        style TEXT DEFAULT 'ICT',
        strength TEXT DEFAULT 'NORMAL',
        symbol TEXT DEFAULT 'XAU/USD'
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
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS bot_settings (
        id {pk},
        setting_key TEXT UNIQUE,
        setting_value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ===== جدول تنظیمات استراتژی‌ها (پارامترهای هر استراتژی، مثل سخت‌گیری) =====
    # کلید به‌صورت "strategy_id.param_name" ذخیره می‌شه، مثلاً "surpri3e.depth"
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS strategy_settings (
        id {pk},
        setting_key TEXT UNIQUE,
        setting_value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ===== جدول دکمه‌های سفارشی که ادمین از پنل مدیریت ساخته =====
    # هر دکمه یا یک متن ثابت (response_text) نمایش می‌ده، یا اگه link_action
    # پر شده باشه، دقیقاً مثل یکی از دکمه‌های موجود ربات عمل می‌کنه
    # (مثلاً همون کاری که دکمه‌ی "دریافت سیگنال" انجام می‌ده).
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS custom_buttons (
        id {pk},
        button_key TEXT UNIQUE,
        label TEXT,
        response_text TEXT,
        link_action TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ===== migration برای دیتابیس‌های قدیمی‌تر که ستون‌های جدید رو ندارن =====
    if not _column_exists(cursor, "custom_buttons", "link_action"):
        cursor.execute("ALTER TABLE custom_buttons ADD COLUMN link_action TEXT")

    if not _column_exists(cursor, "users", "rr_ratio"):
        cursor.execute("ALTER TABLE users ADD COLUMN rr_ratio REAL DEFAULT 2")

    if not _column_exists(cursor, "users", "last_signal_at"):
        cursor.execute("ALTER TABLE users ADD COLUMN last_signal_at TEXT")

    if not _column_exists(cursor, "users", "last_signal_timeframe"):
        cursor.execute("ALTER TABLE users ADD COLUMN last_signal_timeframe TEXT")

    if not _column_exists(cursor, "trades", "strength"):
        cursor.execute("ALTER TABLE trades ADD COLUMN strength TEXT DEFAULT 'NORMAL'")

    if not _column_exists(cursor, "trades", "symbol"):
        cursor.execute("ALTER TABLE trades ADD COLUMN symbol TEXT DEFAULT 'XAU/USD'")

    # ===== migration: پلن و تاریخ انقضای VIP =====
    if not _column_exists(cursor, "users", "vip_plan"):
        cursor.execute("ALTER TABLE users ADD COLUMN vip_plan TEXT")

    if not _column_exists(cursor, "users", "vip_expires_at"):
        cursor.execute("ALTER TABLE users ADD COLUMN vip_expires_at TEXT")

    # ===== migration: شماره تماس کاربر (برای فرآیند احراز هویت پرداخت) =====
    if not _column_exists(cursor, "users", "phone_number"):
        cursor.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")

    # ===== migration: رفع باگ RR مشترک بین مود Standard و Fast Scalp =====
    # قبلاً یک ستون rr_ratio مشترک بود که با انتخاب RR در هر مود بازنویسی
    # می‌شد (یعنی تنظیم RR اسکلپ، RR استاندارد کاربر رو هم پاک می‌کرد).
    # الان هر مود ستون RR جدای خودش رو داره.
    if not _column_exists(cursor, "users", "rr_ratio_standard"):
        cursor.execute("ALTER TABLE users ADD COLUMN rr_ratio_standard REAL DEFAULT 2")

    if not _column_exists(cursor, "users", "rr_ratio_scalp"):
        cursor.execute("ALTER TABLE users ADD COLUMN rr_ratio_scalp REAL DEFAULT 5")
        # ===== مقدار ستون قدیمی rr_ratio (اگه کاربر قبلاً چیزی ست کرده) رو =====
        # ===== به‌عنوان مقدار اولیه‌ی standard منتقل می‌کنیم تا چیزی از دست نره =====
        if _column_exists(cursor, "users", "rr_ratio"):
            cursor.execute("UPDATE users SET rr_ratio_standard = rr_ratio WHERE rr_ratio IS NOT NULL")

    # ===== جدول درخواست‌های پرداخت VIP (رسید ارسالی کاربر تا تایید دستی ادمین) =====
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS vip_payment_requests (
        id {pk},
        user_id INTEGER,
        plan_id TEXT,
        phone_number TEXT,
        receipt_file_id TEXT,
        status TEXT DEFAULT 'PENDING',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ===== migration: کاربرانی که از قبل با style قدیمی (ICT/SMC) ثبت شدن =====
    # چون signals.py دیگه فقط SURPRI3E رو می‌شناسه، این کاربرا باید بروزرسانی بشن
    # وگرنه create_signal همیشه None برمی‌گردونه (باگی که باعث "سیگنال نمی‌ده" می‌شد)
    cursor.execute("UPDATE users SET style='surpri3e' WHERE style IS NULL OR style IN ('ICT', 'SMC')")

    # ===== تنظیمات پیش‌فرض =====
    default_settings = [
        ('daily_signal_limit', '5'),
        ('referral_step_count', '5'),   # هر چند نفر رفرال یک پله‌ست
        ('referral_step_bonus', '3'),   # هر پله چند سیگنال اضافه می‌ده
        ('bot_locked', 'false'),
        ('signal_enabled', 'true'),
        ('channel_locked', 'false'),
        ('vip_card_number', ''),
        ('vip_card_holder', ''),
        ('stop_distance_pips', '30'),    # فاصله‌ی استاپ سراسری (پیپ) - جایگزین منطق ATR/اسکلپ قدیمی
        ('pip_value_xau', '0.1'),        # ارزش هر پیپ برای طلا (دلار) - رایج‌ترین قرارداد بروکرها
        ('pip_value_btc', '1'),          # ارزش هر پیپ برای بیت‌کوین (دلار)
        ('default_timeframe', '5min'),   # تایم‌فریم پیش‌فرض سراسری - کاربر دیگه انتخاب نمی‌کنه
        ('signal_cooldown_minutes', '15'),  # فاصله‌ی زمانی الزامی بین دو سیگنال متوالی هر کاربر (به‌جز ادمین)
    ]

    for key, value in default_settings:
        _insert_ignore("bot_settings", ["setting_key", "setting_value"], conn, cursor, (key, value))

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
    """
    مقدار یک تنظیم رو ذخیره می‌کنه. اگه کلید از قبل وجود نداشته باشه
    (مثلاً تنظیمات داینامیکی مثل نام سفارشی دکمه‌ها که تو لیست
    default_settings اولیه نیستن)، به‌جای نادیده گرفتن، insert می‌کنه.
    """
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO bot_settings (setting_key, setting_value) VALUES (?, ?) "
        "ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value, updated_at=CURRENT_TIMESTAMP",
        (key, value)
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


# ============ سفارشی‌سازی دکمه‌های شیشه‌ای (اسم/حذف) ============
# از همون جدول bot_settings استفاده می‌کنیم، با پیشوند "btn_name_" و "btn_hidden_"
def get_button_label(button_key, default_label):
    """
    اسم نمایشی یک دکمه رو برمی‌گردونه. اگه ادمین از پنل مدیریت اسمش رو
    عوض کرده باشه، همون رو می‌ده؛ وگرنه اسم پیش‌فرض کد.
    """
    custom = get_setting(f"btn_name_{button_key}")
    return custom if custom else default_label


def set_button_label(button_key, new_label):
    """اسم نمایشی یک دکمه رو تغییر می‌ده."""
    update_setting(f"btn_name_{button_key}", new_label)


def is_button_hidden(button_key):
    """چک می‌کنه آیا ادمین این دکمه رو از پنل مدیریت مخفی/حذف کرده."""
    return get_setting(f"btn_hidden_{button_key}") == "true"


def set_button_hidden(button_key, hidden=True):
    """یک دکمه رو مخفی یا نمایان می‌کنه."""
    update_setting(f"btn_hidden_{button_key}", "true" if hidden else "false")


def reset_button_customization(button_key):
    """اسم و وضعیت مخفی‌بودن یک دکمه رو به پیش‌فرض برمی‌گردونه."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bot_settings WHERE setting_key IN (?, ?)",
                   (f"btn_name_{button_key}", f"btn_hidden_{button_key}"))
    conn.commit()
    conn.close()


# ============ دکمه‌های سفارشی (کاملاً جدید، ساخته‌شده توسط ادمین) ============
def add_custom_button(button_key, label, response_text=None, link_action=None):
    """
    یک دکمه‌ی کاملاً جدید می‌سازه.
    اگه link_action پر باشه، دکمه دقیقاً مثل یکی از دکمه‌های موجود ربات
    عمل می‌کنه (مثلاً link_action='signal_menu' یعنی این دکمه هم مثل
    دکمه‌ی «دریافت سیگنال» رفتار می‌کنه). در غیر این صورت، response_text
    (متن ثابت) با کلیک نمایش داده می‌شه.
    """
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO custom_buttons (button_key, label, response_text, link_action) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(button_key) DO UPDATE SET label=excluded.label, response_text=excluded.response_text, link_action=excluded.link_action",
        (button_key, label, response_text, link_action)
    )
    conn.commit()
    conn.close()


def get_all_custom_buttons():
    """همه‌ی دکمه‌های سفارشی رو برمی‌گردونه: لیست dict با button_key, label, response_text, link_action."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT button_key, label, response_text, link_action FROM custom_buttons ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [{'button_key': r[0], 'label': r[1], 'response_text': r[2], 'link_action': r[3]} for r in rows]


def get_custom_button(button_key):
    """یک دکمه‌ی سفارشی خاص رو برمی‌گردونه، یا None اگه پیدا نشه."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT button_key, label, response_text, link_action FROM custom_buttons WHERE button_key=?", (button_key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'button_key': row[0], 'label': row[1], 'response_text': row[2], 'link_action': row[3]}
    return None


def delete_custom_button(button_key):
    """یک دکمه‌ی سفارشی رو کامل حذف می‌کنه."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_buttons WHERE button_key=?", (button_key,))
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

    cursor.execute("""
    INSERT INTO users (id, username, first_name, last_name, joined_at, last_active, lang, daily_signal_limit, rr_ratio_standard, rr_ratio_scalp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        first_name,
        last_name,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        lang,
        5,
        DEFAULT_RR_STANDARD,
        DEFAULT_RR_SCALP
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
    cursor.execute(
        "SELECT id, last_active, is_vip, referral_count, lang, style, vip_plan, vip_expires_at "
        "FROM users ORDER BY id DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [{
        'id': r[0], 'last_active': r[1], 'is_vip': bool(r[2]), 'referral_count': r[3],
        'lang': r[4], 'style': r[5], 'vip_plan': r[6], 'vip_expires_at': r[7]
    } for r in rows]


def get_user_lang(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'fa'


def get_user_display_info(user_id):
    """
    اطلاعات نمایشی کاربر (یوزرنیم + آیدی عددی) رو برمی‌گردونه - برای
    مواقعی که ادمین باید کاربر رو راحت شناسایی کنه (مثلاً موقع تایید
    پرداخت VIP). آیدی عددی همیشه از خودِ تلگرام گرفته می‌شه (قابل جعل
    نیست)، پس همیشه همینو مبنای اصلی VIP کردن قرار می‌دیم - یوزرنیم فقط
    برای راحتی شناسایی توسط ادمینه.
    """
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT username, first_name FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        username, first_name = result
        username_part = f"@{username}" if username else (first_name or "—")
        return f"{username_part} (`{user_id}`)"
    return f"`{user_id}`"


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


# ============ VIP: پلن‌ها، انقضا، شماره کارت ============

# تعریف پلن‌های VIP - قیمت‌ها به تومان
VIP_PLANS = {
    "1m": {"label": "۱ ماهه", "days": 30, "price_toman": 500_000},
    "3m": {"label": "۳ ماهه", "days": 90, "price_toman": 1_400_000},
    "6m": {"label": "۶ ماهه", "days": 180, "price_toman": 2_900_000},
    "12m": {"label": "۱۲ ماهه", "days": 365, "price_toman": 4_800_000},
}


def set_user_vip_plan(user_id, plan_id):
    """
    کاربر رو VIP می‌کنه با یک پلن مشخص، و تاریخ انقضا رو بر اساس مدت پلن
    محاسبه می‌کنه. فقط زمانی صدا زده می‌شه که ادمین دستی پرداخت رو تایید کند.
    """
    if plan_id not in VIP_PLANS:
        return False

    days = VIP_PLANS[plan_id]["days"]
    expires_at = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET is_vip=1, vip_plan=?, vip_expires_at=? WHERE id=?",
        (plan_id, expires_at, user_id)
    )
    conn.commit()
    conn.close()
    return True


def get_user_vip_status(user_id):
    """
    وضعیت VIP کاربر رو برمی‌گردونه: dict شامل is_vip, plan, plan_label,
    expires_at, days_left. اگه اشتراک منقضی شده باشه، خودکار is_vip رو
    False می‌کنه (هم در دیتابیس هم در خروجی) تا هیچ‌جای دیگه‌ی کد لازم
    نباشه جداگانه چک تاریخ انقضا انجام بده.
    """
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT is_vip, vip_plan, vip_expires_at FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return {'is_vip': False, 'plan': None, 'plan_label': None, 'expires_at': None, 'days_left': 0}

    is_vip, plan, expires_at_str = result

    if is_vip and expires_at_str:
        try:
            expires_at = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            expires_at = None

        if expires_at and expires_at < datetime.now():
            # ===== اشتراک منقضی شده - خودکار غیرفعال کن =====
            cursor.execute("UPDATE users SET is_vip=0 WHERE id=?", (user_id,))
            conn.commit()
            conn.close()
            return {'is_vip': False, 'plan': plan, 'plan_label': VIP_PLANS.get(plan, {}).get('label'),
                    'expires_at': expires_at_str, 'days_left': 0}

        days_left = (expires_at - datetime.now()).days if expires_at else None
        conn.close()
        return {
            'is_vip': True,
            'plan': plan,
            'plan_label': VIP_PLANS.get(plan, {}).get('label', '—'),
            'expires_at': expires_at_str,
            'days_left': max(0, days_left) if days_left is not None else None,
        }

    conn.close()
    return {'is_vip': bool(is_vip), 'plan': plan, 'plan_label': VIP_PLANS.get(plan, {}).get('label'),
            'expires_at': expires_at_str, 'days_left': None}


def set_user_phone(user_id, phone_number):
    """شماره تماس کاربر رو ذخیره می‌کنه (برای فرآیند احراز هویت پرداخت VIP)."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET phone_number=? WHERE id=?", (phone_number, user_id))
    conn.commit()
    conn.close()


def get_user_phone(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT phone_number FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def create_vip_payment_request(user_id, plan_id, phone_number, receipt_file_id):
    """
    یک درخواست پرداخت VIP جدید ثبت می‌کنه (بعد از این‌که کاربر عکس رسید
    رو فرستاد). این فقط ثبت اطلاعات است - VIP کردن کاربر همیشه باید
    توسط ادمین از پنل مدیریت به‌صورت دستی تایید بشه.
    """
    conn = connect()
    cursor = conn.cursor()
    request_id = _insert_returning_id(
        "INSERT INTO vip_payment_requests (user_id, plan_id, phone_number, receipt_file_id, status) "
        "VALUES (?, ?, ?, ?, 'PENDING')",
        (user_id, plan_id, phone_number, receipt_file_id),
        cursor
    )
    conn.commit()
    conn.close()
    return request_id


def get_vip_payment_request(request_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, plan_id, phone_number, receipt_file_id, status FROM vip_payment_requests WHERE id=?",
        (request_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'user_id': row[1], 'plan_id': row[2], 'phone_number': row[3],
                'receipt_file_id': row[4], 'status': row[5]}
    return None


def update_vip_payment_status(request_id, status):
    """وضعیت درخواست رو به‌روزرسانی می‌کنه (مثلاً 'APPROVED' یا 'REJECTED')."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE vip_payment_requests SET status=? WHERE id=?", (status, request_id))
    conn.commit()
    conn.close()


def get_pending_vip_requests():
    """همه‌ی درخواست‌های پرداخت VIP در انتظار بررسی رو برمی‌گردونه."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, plan_id, phone_number, created_at FROM vip_payment_requests "
        "WHERE status='PENDING' ORDER BY id DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'user_id': r[1], 'plan_id': r[2], 'phone_number': r[3], 'created_at': r[4]} for r in rows]


def set_vip_card_info(card_number, card_holder=None):
    """شماره کارت (و اختیاری نام صاحب کارت) که برای پرداخت VIP نمایش داده می‌شه رو تنظیم می‌کنه."""
    update_setting('vip_card_number', card_number)
    if card_holder is not None:
        update_setting('vip_card_holder', card_holder)


def get_vip_card_info():
    """شماره کارت و نام صاحب کارت رو برمی‌گردونه."""
    return {
        'card_number': get_setting('vip_card_number') or '',
        'card_holder': get_setting('vip_card_holder') or '',
    }


# ============ RR اختصاصی هر کاربر - جدا برای هر مود (رفع باگ) ============
# ⚠️ قبلاً یک ستون rr_ratio مشترک بین دو مود Standard و Fast Scalp بود:
# انتخاب RR در یکی از مودها، RR مود دیگه رو هم بازنویسی می‌کرد. الان هر
# کاربر دو مقدار کاملاً جدا داره: rr_ratio_standard و rr_ratio_scalp.
#
# پیش‌فرض‌ها متفاوتن چون طبیعت دو مود فرق داره: Standard پیش‌فرض RR=2،
# Fast Scalp پیش‌فرض RR=5 (طبق تصمیم پروژه - اسکلپ نوسان کوچیک‌تری
# می‌گیره پس برای سودآوری معمولاً RR بالاتری لازم داره).
DEFAULT_RR_STANDARD = 2.0
DEFAULT_RR_SCALP = 5.0


def set_user_rr(user_id, rr_value, mode='standard'):
    """
    نسبت RR مخصوص همین کاربر رو ذخیره می‌کنه - جدا برای هر مود.
    mode: 'standard' یا 'fast_scalp' (هرچیز غیر از 'fast_scalp' به‌عنوان
    'standard' در نظر گرفته می‌شه).
    """
    column = "rr_ratio_scalp" if mode == "fast_scalp" else "rr_ratio_standard"
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {column}=? WHERE id=?", (float(rr_value), user_id))
    conn.commit()
    conn.close()


def get_user_rr(user_id, mode='standard'):
    """RR اختصاصی کاربر رو برای مود مشخص‌شده برمی‌گردونه؛ اگه ذخیره نشده، مقدار پیش‌فرض همون مود."""
    column = "rr_ratio_scalp" if mode == "fast_scalp" else "rr_ratio_standard"
    default_value = DEFAULT_RR_SCALP if mode == "fast_scalp" else DEFAULT_RR_STANDARD

    conn = connect()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {column} FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0] is not None:
        return float(result[0])
    return default_value


# ============ Cooldown سیگنال بر اساس تایم‌فریم ============
# ============================================================
# ⚠️ تغییر مهم (۲۰۲۶-۰۷-۲۱): قبلاً فاصله‌ی مجاز بین دو سیگنال بر اساس
# طول خود تایم‌فریم بود (مثلاً روی ۱ ساعته، ۱ ساعت صبر). طبق تصمیم
# پروژه، الان یک عدد ثابت و سراسری (پیش‌فرض ۱۵ دقیقه) از پنل ادمین
# جایگزین شده - برای همه‌ی کاربران و همه‌ی تایم‌فریم‌ها یکسانه.
# این محدودیت شامل ادمین نمی‌شه (طبق تصمیم پروژه).
# ============================================================


def check_signal_cooldown(user_id, timeframe=None):
    """
    بررسی می‌کنه آیا کاربر مجاز به درخواست سیگنال جدیده یا باید صبر کنه.
    فاصله‌ی مجاز، عدد ثابت سراسری «signal_cooldown_minutes» از پنل
    ادمینه - نه وابسته به تایم‌فریم. این محدودیت شامل ادمین نمی‌شه.

    پارامتر timeframe دیگه در محاسبه استفاده نمی‌شه (فقط برای سازگاری
    با فراخوانی‌های قدیمی نگه داشته شده).

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
        "SELECT last_signal_at FROM users WHERE id=?",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()

    if not result or not result[0]:
        return True, 0

    last_signal_at_str = result[0]
    try:
        last_signal_at = datetime.strptime(last_signal_at_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return True, 0

    cooldown_minutes = float(get_setting('signal_cooldown_minutes') or '15')
    cooldown = cooldown_minutes * 60
    elapsed = (datetime.now() - last_signal_at).total_seconds()

    if elapsed >= cooldown:
        return True, 0

    return False, int(cooldown - elapsed)


def record_signal_time(user_id, timeframe=None):
    """بعد از تولید موفق سیگنال صدا زده می‌شه تا زمان آخرین سیگنال ثبت بشه."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_signal_at=? WHERE id=?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id)
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
    """
    سقف سیگنال روزانه‌ی کاربر رو بر اساس تعداد رفرال‌هاش دوباره محاسبه می‌کنه.

    منطق: به ازای هر «referral_step_count» نفر که کاربر دعوت کرده،
    «referral_step_bonus» سیگنال اضافه به سقف پایه (۵) اضافه می‌شه.
    مثال پیش‌فرض: هر ۵ نفر رفرال => +۳ سیگنال روزانه.
    هر دو مقدار از پنل ادمین قابل تغییرن (بدون نیاز به دست‌زدن به کد).
    """
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT referral_count FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()

    if result:
        referral_count = result[0] or 0
        step_count = int(get_setting('referral_step_count') or '5')
        step_bonus = int(get_setting('referral_step_bonus') or '3')
        base_limit = int(get_setting('daily_signal_limit') or '5')

        if step_count > 0 and referral_count > 0:
            steps_completed = referral_count // step_count
            extra_signals = steps_completed * step_bonus
            new_limit = base_limit + extra_signals
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
def save_trade(signal, user_id=0, style='ICT', strength='NORMAL', symbol='XAU/USD'):
    conn = connect()
    cursor = conn.cursor()

    trade_id = _insert_returning_id("""
    INSERT INTO trades (time, direction, entry, sl, tp, result, user_id, style, strength, symbol)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        signal["direction"],
        signal["entry"],
        signal["sl"],
        signal["tp"],
        "OPEN",
        user_id,
        style,
        strength,
        symbol
    ), cursor)

    conn.commit()
    conn.close()
    return trade_id


def update_result(trade_id, result):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE trades SET result=? WHERE id=?", (result, trade_id))
    conn.commit()
    conn.close()


def get_open_trades():
    """
    همه‌ی معاملاتی که هنوز نتیجه‌شون OPEN است رو برمی‌گردونه (برای چک خودکار TP/SL).
    خروجی: لیست dict با فیلدهای id, user_id, direction, entry, sl, tp, symbol
    """
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, direction, entry, sl, tp, symbol
        FROM trades WHERE result='OPEN'
    """)
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            'id': r[0], 'user_id': r[1], 'direction': r[2], 'entry': r[3],
            'sl': r[4], 'tp': r[5], 'symbol': r[6] if r[6] else 'XAU/USD'
        }
        for r in rows
    ]


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


def get_user_pnl_stats(user_id, risk_percent, period='weekly'):
    """
    محاسبه‌ی سود/زیان و Profit Factor کاربر، با فرض این‌که کاربر روی هر
    معامله دقیقاً «risk_percent» درصد از سرمایه‌ی خودش رو ریسک کرده.

    منطق محاسبه:
      - RR واقعی هر معامله از روی entry/sl/tp خودِ همون معامله محاسبه می‌شه:
        RR = |tp - entry| / |entry - sl|
        (این دقیق‌تر از فرض RR ثابت است، چون واقعاً همون RR ای است که
        استراتژی برای اون معامله‌ی خاص محاسبه کرده بود.)
      - هر معامله‌ی TP: سود = risk_percent × RR همون معامله
      - هر معامله‌ی SL: ضرر = risk_percent (کامل)
      - Profit Factor = مجموع سودها / مجموع ضررها (اگه ضرری نباشه، None برگردونده می‌شه)
      - درصد سود کلی = مجموع سود - مجموع ضرر (بر حسب درصد سرمایه، جمع‌پذیر ساده -
        نه ترکیبی/compounding، چون فرض بر ریسک ثابت روی سرمایه‌ی اولیه است)

    period: 'weekly' (۷ روز اخیر) یا 'monthly' (۳۰ روز اخیر) یا 'all_time'

    خروجی: dict شامل total, wins, losses, winrate, total_profit_percent,
    total_loss_percent, net_percent, profit_factor
    """
    conn = connect()
    cursor = conn.cursor()

    if period == 'weekly':
        since = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M')
        cursor.execute(
            "SELECT entry, sl, tp, result FROM trades WHERE user_id=? AND time >= ? AND result IN ('TP','SL')",
            (user_id, since)
        )
    elif period == 'monthly':
        since = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M')
        cursor.execute(
            "SELECT entry, sl, tp, result FROM trades WHERE user_id=? AND time >= ? AND result IN ('TP','SL')",
            (user_id, since)
        )
    else:
        cursor.execute(
            "SELECT entry, sl, tp, result FROM trades WHERE user_id=? AND result IN ('TP','SL')",
            (user_id,)
        )

    rows = cursor.fetchall()
    conn.close()

    risk_percent = float(risk_percent)
    total = len(rows)
    wins = 0
    losses = 0
    total_profit_percent = 0.0
    total_loss_percent = 0.0

    for entry, sl, tp, result in rows:
        try:
            entry, sl, tp = float(entry), float(sl), float(tp)
            risk_distance = abs(entry - sl)
            if risk_distance <= 0:
                continue  # داده‌ی معیوب - نادیده بگیر
            reward_distance = abs(tp - entry)
            trade_rr = reward_distance / risk_distance
        except (TypeError, ValueError, ZeroDivisionError):
            continue

        if result == 'TP':
            wins += 1
            total_profit_percent += risk_percent * trade_rr
        elif result == 'SL':
            losses += 1
            total_loss_percent += risk_percent

    winrate = round((wins / total) * 100, 2) if total > 0 else 0
    net_percent = round(total_profit_percent - total_loss_percent, 2)
    profit_factor = round(total_profit_percent / total_loss_percent, 2) if total_loss_percent > 0 else None

    return {
        'total': total,
        'wins': wins,
        'losses': losses,
        'winrate': winrate,
        'risk_percent': risk_percent,
        'total_profit_percent': round(total_profit_percent, 2),
        'total_loss_percent': round(total_loss_percent, 2),
        'net_percent': net_percent,
        'profit_factor': profit_factor,
    }
