# ============ تنظیمات ربات ============
def init_settings_table():
    """ایجاد جدول تنظیمات"""
    conn = connect()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE,
        setting_value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # تنظیمات پیش‌فرض
    default_settings = [
        ('daily_signal_limit', '5'),
        ('referral_bonus', '1'),
        ('referral_threshold', '5'),
        ('rr_ratio', '2'),
        ('default_timeframe', '1h'),
        ('bot_locked', 'false'),
        ('signal_enabled', 'true'),
        ('ai_enabled', 'true'),
        ('vip_enabled', 'true'),
        ('max_signals_per_day', '10'),
        ('min_rsi', '30'),
        ('max_rsi', '70')
    ]
    
    for key, value in default_settings:
        cursor.execute(
            "INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)",
            (key, value)
        )
    
    conn.commit()
    conn.close()

def get_setting(key):
    """دریافت یک تنظیم"""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT setting_value FROM bot_settings WHERE setting_key=?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def update_setting(key, value):
    """بروزرسانی یک تنظیم"""
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
    """دریافت همه تنظیمات"""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT setting_key, setting_value FROM bot_settings")
    results = cursor.fetchall()
    conn.close()
    return {key: value for key, value in results}
