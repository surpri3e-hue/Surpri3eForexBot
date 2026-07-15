from database import (
    get_setting, update_setting, get_all_settings,
    get_users_count, get_all_users, set_user_vip, delete_user,
    reset_daily_signals, get_active_users_today, get_today_stats,
    get_statistics, connect
)
from datetime import datetime
import pytz
import logging

TEHRAN_TZ = pytz.timezone('Asia/Tehran')

# ============ کنترل‌های اصلی ============
def toggle_bot_lock():
    current = get_setting('bot_locked') == 'true'
    new_status = not current
    update_setting('bot_locked', 'true' if new_status else 'false')
    return '🔒 قفل شده' if new_status else '🔓 باز'

def toggle_signal():
    current = get_setting('signal_enabled') == 'true'
    new_status = not current
    update_setting('signal_enabled', 'true' if new_status else 'false')
    return '🚀 فعال' if new_status else '⛔ غیرفعال'

def toggle_channel_lock():
    current = get_setting('channel_locked') == 'true'
    new_status = not current
    update_setting('channel_locked', 'true' if new_status else 'false')
    return '🔒 فعال' if new_status else '🔓 غیرفعال'

# ============ تنظیمات سیگنال ============
def set_daily_signal_limit(value):
    """تنظیم تعداد سیگنال روزانه برای همه کاربران"""
    try:
        value = int(value)
        if value <= 0:
            return "❌ مقدار باید بزرگتر از صفر باشد."

        update_setting('daily_signal_limit', str(value))

        # اعمال روی همه کاربران
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET daily_signal_limit=?", (value,))
        conn.commit()
        conn.close()

        return f"✅ تعداد سیگنال روزانه به {value} تغییر کرد و روی همه کاربران اعمال شد."
    except:
        return "❌ لطفاً یک عدد معتبر وارد کنید."

def set_rr_ratio(value):
    try:
        value = float(value)
        if value <= 0:
            return "❌ مقدار باید بزرگتر از صفر باشد."
        update_setting('rr_ratio', str(value))
        return f"✅ نسبت RR به 1:{value} تغییر کرد."
    except:
        return "❌ لطفاً یک عدد معتبر وارد کنید."

def set_default_timeframe(value):
    if value not in ['1min', '5min', '15min', '1h', '4h', '1d']:
        return "❌ تایم‌فریم نامعتبر"
    update_setting('default_timeframe', value)
    return f"✅ تایم‌فریم پیش‌فرض: {value}"

# ============ سیستم رفرال ============
def set_referral_bonus(value):
    try:
        value = int(value)
        if value <= 0:
            return "❌ مقدار باید بزرگتر از صفر باشد."
        update_setting('referral_bonus', str(value))
        return f"✅ پاداش هر رفرال: {value} سیگنال اضافی"
    except:
        return "❌ لطفاً یک عدد معتبر وارد کنید."

def set_referral_threshold(value):
    try:
        value = int(value)
        if value <= 0:
            return "❌ مقدار باید بزرگتر از صفر باشد."
        update_setting('referral_threshold', str(value))
        return f"✅ آستانه رفرال: {value}"
    except:
        return "❌ لطفاً یک عدد معتبر وارد کنید."

# ============ داشبورد ============
def dashboard():
    settings = get_all_settings()
    users = get_users_count()
    active = get_active_users_today()
    today_stats = get_today_stats()

    return f"""
📊 **داشبورد مدیریت**

👥 **کاربران:** {users}
📈 **فعال امروز:** {active}
📊 **سیگنال روزانه:** {settings.get('daily_signal_limit', '5')}
🎯 **نسبت RR:** 1:{settings.get('rr_ratio', '2')}
⏱️ **تایم‌فریم:** {settings.get('default_timeframe', '1h')}

🔒 **وضعیت ربات:** {'🔒 قفل' if settings.get('bot_locked') == 'true' else '🔓 باز'}
🚀 **سیگنال:** {'✅ فعال' if settings.get('signal_enabled') == 'true' else '❌ غیرفعال'}
🔒 **قفل کانال:** {'✅ فعال' if settings.get('channel_locked') == 'true' else '❌ غیرفعال'}

📊 **آمار امروز:**
• سیگنال‌های استفاده شده: {today_stats['signals_used']}
• TP ثبت شده: {today_stats['tp_count']}
• SL ثبت شده: {today_stats['sl_count']}

🔄 **سیستم رفرال:**
• پاداش: {settings.get('referral_bonus', '1')} سیگنال
• آستانه: {settings.get('referral_threshold', '5')} رفرال

📡 **آخرین بروزرسانی:** {datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d %H:%M')}
"""

def report():
    stats = get_statistics()
    today_stats = get_today_stats()
    users = get_users_count()

    return f"""
📊 **گزارش کامل**

👥 **کل کاربران:** {users}
📈 **کل معاملات:** {stats['total']}
✅ **برنده:** {stats['wins']}
❌ **بازنده:** {stats['losses']}
🎯 **نرخ موفقیت:** {stats['winrate']}%

📊 **آمار امروز:**
• سیگنال‌های استفاده شده: {today_stats['signals_used']}
• TP ثبت شده: {today_stats['tp_count']}
• SL ثبت شده: {today_stats['sl_count']}

📡 **تاریخ:** {datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d %H:%M')}
"""

# ============ ریست شبانه ============
def reset_daily():
    reset_daily_signals()
    logging.info("🔄 سیگنال‌های روزانه ریست شد.")
    return "✅ سیگنال‌های روزانه ریست شد"

def get_user_detail(user_id):
    """گرفتن جزئیات یک کاربر"""
    from database import connect
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, first_name, last_name, joined_at, last_active,
               is_vip, referral_count, daily_signal_limit, signals_used_today, lang, style
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
            'style': result[11] if len(result) > 11 else 'ICT'
        }
    return None
