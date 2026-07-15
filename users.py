# users.py (قسمت‌های اضافه شده)

def get_referral_link(user_id):
    """گرفتن لینک رفرال کاربر"""
    bot_username = os.getenv("BOT_USERNAME", "Surpri3eFXbot")
    return f"https://t.me/{bot_username}?start=ref_{user_id}"

def process_referral(user_id, referrer_id):
    """پردازش رفرال"""
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

def is_user_vip(user_id):
    """بررسی VIP بودن کاربر"""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT is_vip FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return bool(result[0]) if result else False

def get_user_signals_left(user_id):
    """دریافت تعداد سیگنال باقی‌مانده (با در نظر گرفتن VIP)"""
    # اگر کاربر ادمین باشد، محدودیت ندارد
    ADMIN_ID = int(os.getenv("ADMIN_ID", 816822644))
    if user_id == ADMIN_ID:
        return 999
    
    # اگر کاربر VIP باشد، محدودیت ندارد
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
    """استفاده از یک سیگنال (با در نظر گرفتن VIP)"""
    if user_id == int(os.getenv("ADMIN_ID", 816822644)):
        return True
    
    if is_user_vip(user_id):
        return True
    
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET signals_used_today = signals_used_today + 1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return True
