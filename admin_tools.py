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

        conn = connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET daily_signal_limit=?", (value,))
        conn.commit()
        conn.close()

        return f"✅ تعداد سیگنال روزانه به {value} تغییر کرد و روی همه کاربران اعمال شد."
    except Exception:
        return "❌ لطفاً یک عدد معتبر وارد کنید."


def set_default_timeframe(value):
    """
    تنظیم تایم‌فریم پیش‌فرض سراسری که برای همه‌ی کاربران اعمال می‌شه.
    کاربر دیگه خودش تایم‌فریم رو انتخاب نمی‌کنه - این مقدار سراسری
    همیشه استفاده می‌شه.
    """
    valid_timeframes = ['1min', '5min', '15min', '30min', '1h', '4h', '1d']
    if value not in valid_timeframes:
        return f"❌ تایم‌فریم نامعتبر. گزینه‌های مجاز: {', '.join(valid_timeframes)}"
    update_setting('default_timeframe', value)
    return f"✅ تایم‌فریم پیش‌فرض برای همه‌ی کاربران به {value} تغییر کرد."


def set_signal_cooldown(value):
    """
    تنظیم فاصله‌ی زمانی الزامی (به دقیقه) بین دو سیگنال متوالی هر کاربر.
    این محدودیت شامل ادمین نمی‌شه (طبق تصمیم پروژه).
    """
    try:
        value = float(value)
        if value <= 0:
            return "❌ مقدار باید بزرگتر از صفر باشد."
        update_setting('signal_cooldown_minutes', str(value))
        return f"✅ فاصله‌ی بین سیگنال‌ها برای همه‌ی کاربران (به‌جز ادمین) به {value} دقیقه تغییر کرد."
    except Exception:
        return "❌ لطفاً یک عدد معتبر وارد کنید."


# ============ سیستم رفرال ============
def set_referral_step(step_count, step_bonus):
    """
    تنظیم یکجای قانون رفرال: هر «step_count» نفر رفرال، «step_bonus»
    سیگنال اضافه به سقف روزانه‌ی کاربر اضافه می‌شه.
    (جایگزین دو تنظیم جدای قبلی referral_bonus/referral_threshold که
    گیج‌کننده بودن؛ الان یک پنل واحد و روشن.)
    """
    try:
        step_count = int(step_count)
        step_bonus = int(step_bonus)
        if step_count <= 0 or step_bonus <= 0:
            return "❌ هر دو مقدار باید بزرگتر از صفر باشند."
        update_setting('referral_step_count', str(step_count))
        update_setting('referral_step_bonus', str(step_bonus))
        return f"✅ قانون رفرال تنظیم شد: هر {step_count} نفر رفرال ⇽ {step_bonus} سیگنال اضافه"
    except Exception:
        return "❌ لطفاً دو عدد معتبر وارد کنید (مثال: 5,3)."


# ============ داشبورد ============
def dashboard():
    import os
    settings = get_all_settings()
    users = get_users_count()
    active = get_active_users_today()
    today_stats = get_today_stats()

    twelve_data_key = os.getenv("TWELVE_DATA")
    if twelve_data_key:
        key_preview = f"{twelve_data_key[:4]}...{twelve_data_key[-4:]}" if len(twelve_data_key) > 8 else "تنظیم شده"
        api_status = f"✅ تنظیم شده ({key_preview})"
    else:
        api_status = "❌ تنظیم نشده - سیگنال‌ها روی داده‌ی تستی (غیرواقعی) کار می‌کنند!"

    return f"""
📊 **داشبورد مدیریت**

🔑 **کلید Twelve Data:** {api_status}

👥 **کاربران:** {users}
📈 **فعال امروز:** {active}
📊 **سیگنال روزانه:** {settings.get('daily_signal_limit', '5')}
⏱️ **تایم‌فریم پیش‌فرض:** {settings.get('default_timeframe', '5min')}
⏳ **فاصله‌ی بین سیگنال‌ها:** {settings.get('signal_cooldown_minutes', '15')} دقیقه

🔒 **وضعیت ربات:** {'🔒 قفل' if settings.get('bot_locked') == 'true' else '🔓 باز'}
🚀 **سیگنال:** {'✅ فعال' if settings.get('signal_enabled') == 'true' else '❌ غیرفعال'}
🔒 **قفل کانال:** {'✅ فعال' if settings.get('channel_locked') == 'true' else '❌ غیرفعال'}

📊 **آمار امروز:**
• سیگنال‌های استفاده شده: {today_stats['signals_used']}
• TP ثبت شده: {today_stats['tp_count']}
• SL ثبت شده: {today_stats['sl_count']}

🔄 **سیستم رفرال:**
• هر {settings.get('referral_step_count', '5')} نفر رفرال ⇽ {settings.get('referral_step_bonus', '3')} سیگنال اضافه

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
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, first_name, last_name, joined_at, last_active,
               is_vip, referral_count, daily_signal_limit, signals_used_today, lang, style, rr_ratio
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
            'style': result[11] if len(result) > 11 else 'ICT',
            'rr_ratio': result[12] if len(result) > 12 else 2.0
        }
    return None
