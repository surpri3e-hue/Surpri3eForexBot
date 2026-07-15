# database.py (قسمت‌های اضافه شده)

def add_user(user_id, username=None, first_name=None, last_name=None, lang='fa'):
    conn = connect()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if cursor.fetchone():
        # به‌روزرسانی زبان
        cursor.execute("UPDATE users SET lang=? WHERE id=?", (lang, user_id))
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

def get_user_lang(user_id):
    """دریافت زبان کاربر"""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'fa'

def get_user_style(user_id):
    """دریافت سبک معاملاتی کاربر"""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT style FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'ICT'
