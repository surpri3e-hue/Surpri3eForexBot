# admin_tools.py
from database import get_setting, update_setting, get_all_settings
from users import get_users_count, get_all_users, set_user_vip, delete_user, reset_daily_signals, get_active_users_today
from datetime import datetime
import pytz

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
    try:
        value = int(value)
        if value <= 0:
            return "❌ مقدار باید بزرگتر از صفر باشد."
        update_setting('daily_signal_limit', str(value))
        return f"✅ تعداد سیگنال روزانه به {value} تغییر کرد."
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
    valid = ['15min', '1h', '4h', '1d']
    if value not in valid:
        return f"❌ تایم‌فریم نامعتبر. گزینه‌ها: {', '.join(valid)}"
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

📡 **آخرین بروزرسانی:** {datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d %H:%M')}
"""

def report():
    from database import get_statistics, get_today_stats
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
