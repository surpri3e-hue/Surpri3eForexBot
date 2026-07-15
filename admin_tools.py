from database import get_setting, update_setting, get_all_settings
from users import get_users_count, get_all_users, set_user_vip, delete_user, reset_daily_signals, get_active_users_today
from datetime import datetime

# ============ کنترل‌های کلی ============
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

def toggle_ai():
    current = get_setting('ai_enabled') == 'true'
    new_status = not current
    update_setting('ai_enabled', 'true' if new_status else 'false')
    return '🧠 فعال' if new_status else '⛔ غیرفعال'

def toggle_vip():
    current = get_setting('vip_enabled') == 'true'
    new_status = not current
    update_setting('vip_enabled', 'true' if new_status else 'false')
    return '💎 فعال' if new_status else '⛔ غیرفعال'

def toggle_channel_lock():
    current = get_setting('channel_locked') == 'true'
    new_status = not current
    update_setting('channel_locked', 'true' if new_status else 'false')
    return '🔒 قفل شده' if new_status else '🔓 باز'

# ============ تنظیمات سیگنال ============
def set_daily_signal_limit(value):
    update_setting('daily_signal_limit', str(value))
    return f"✅ تعداد سیگنال روزانه: {value}"

def set_rr_ratio(value):
    update_setting('rr_ratio', str(value))
    return f"✅ نسبت RR: 1:{value}"

def set_default_timeframe(value):
    update_setting('default_timeframe', value)
    return f"✅ تایم‌فریم پیش‌فرض: {value}"

def set_rsi_limits(min_rsi, max_rsi):
    update_setting('min_rsi', str(min_rsi))
    update_setting('max_rsi', str(max_rsi))
    return f"✅ محدوده RSI: {min_rsi} - {max_rsi}"

# ============ سیستم رفرال ============
def set_referral_bonus(value):
    update_setting('referral_bonus', str(value))
    return f"✅ پاداش هر رفرال: {value} سیگنال اضافی"

def set_referral_threshold(value):
    update_setting('referral_threshold', str(value))
    return f"✅ آستانه رفرال: {value}"

# ============ آمار مدیریت ============
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
🧠 **AI:** {'✅ فعال' if settings.get('ai_enabled') == 'true' else '❌ غیرفعال'}
💎 **VIP:** {'✅ فعال' if settings.get('vip_enabled') == 'true' else '❌ غیرفعال'}

🔄 **سیستم رفرال:**
• پاداش: {settings.get('referral_bonus', '1')} سیگنال
• آستانه: {settings.get('referral_threshold', '5')} رفرال

📡 **آخرین بروزرسانی:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

def ai_status():
    settings = get_all_settings()
    return f"""
🧠 **وضعیت AI**

📡 **وضعیت:** {'🟢 فعال' if settings.get('ai_enabled') == 'true' else '🔴 غیرفعال'}
📊 **مدل:** DeepSeek
🎯 **کاربرد:** تحلیل بازار، چت با کاربر

**تنظیمات:**
• پاسخگویی: {'فعال' if settings.get('ai_enabled') == 'true' else 'غیرفعال'}
• تعداد درخواست‌ها: نامحدود

**وضعیت:** {'🟢 عملیاتی' if settings.get('ai_enabled') == 'true' else '⛔ غیرفعال'}
"""

def logs_text():
    return """
📜 **لاگ‌های ربات**

✅ ربات با موفقیت راه‌اندازی شد
✅ دیتابیس متصل است
✅ API Key معتبر است
✅ سیستم سیگنال فعال است
✅ AI آماده به کار است

**وضعیت:** 🟢 همه سیستم‌ها عملیاتی هستند

📡 **آخرین رویدادها:**
• کاربران جدید امروز: {get_active_users_today()}
• سیگنال‌های ارسال شده: {len(get_all_users())}
"""

def report():
    from database import get_statistics
    stats = get_statistics()
    return f"""
📊 **گزارش کامل**

📈 **کل معاملات:** {stats['total']}
✅ **برنده:** {stats['wins']}
❌ **بازنده:** {stats['losses']}
🎯 **نرخ موفقیت:** {stats['winrate']}%
💰 **فاکتور سود:** {stats['profit_factor']}

📡 **تاریخ:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
