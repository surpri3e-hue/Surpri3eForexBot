from database import get_setting, update_setting, get_all_settings
from users import get_users_count, get_all_users, set_user_vip, delete_user, reset_daily_signals, get_active_users_today
from datetime import datetime
import pytz

TEHRAN_TZ = pytz.timezone('Asia/Tehran')

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

def set_daily_signal_limit(value):
    update_setting('daily_signal_limit', str(value))
    return f"✅ تعداد سیگنال روزانه: {value}"

def set_rr_ratio(value):
    update_setting('rr_ratio', str(value))
    return f"✅ نسبت RR: 1:{value}"

def set_default_timeframe(value):
    update_setting('default_timeframe', value)
    return f"✅ تایم‌فریم پیش‌فرض: {value}"

def set_referral_bonus(value):
    update_setting('referral_bonus', str(value))
    return f"✅ پاداش هر رفرال: {value} سیگنال اضافی"

def set_referral_threshold(value):
    update_setting('referral_threshold', str(value))
    return f"✅ آستانه رفرال: {value}"

def dashboard():
    settings = get_all_settings()
    users = get_users_count()
    active = get_active_users_today()

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

🔄 **سیستم رفرال:**
• پاداش: {settings.get('referral_bonus', '1')} سیگنال
• آستانه: {settings.get('referral_threshold', '5')} رفرال

📡 **آخرین بروزرسانی:** {datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d %H:%M')}
"""

def get_today_stats():
    from database import connect
    conn = connect()
    cursor = conn.cursor()
    today = datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) FROM trades WHERE date(time)=?", (today,))
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM trades WHERE date(time)=? AND result='TP'", (today,))
    tp = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM trades WHERE date(time)=? AND result='SL'", (today,))
    sl = cursor.fetchone()[0]
    conn.close()
    return {'signals_used': total, 'tp_count': tp, 'sl_count': sl}

def report():
    stats = get_today_stats()
    return f"""
📊 **گزارش روزانه**

📊 **سیگنال‌های استفاده شده:** {stats['signals_used']}
✅ **TP ثبت شده:** {stats['tp_count']}
❌ **SL ثبت شده:** {stats['sl_count']}

📡 **تاریخ:** {datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d')}
"""
