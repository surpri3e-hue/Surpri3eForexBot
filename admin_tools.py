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
    valid = ['1min', '5min', '15min', '1h', '4h', '1d']
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

# ============ ویرایش دکمه‌ها ============
def edit_button_name(button_key, new_name):
    """ویرایش اسم دکمه‌ها"""
    from database import update_setting
    update_setting(f'button_{button_key}', new_name)
    return f"✅ دکمه با موفقیت به '{new_name}' تغییر کرد."

def get_all_buttons(lang='fa'):
    """دریافت همه دکمه‌ها با اسم‌های سفارشی"""
    from database import get_setting
    default_buttons = {
        'signal_btn': '🚨 دریافت سیگنال',
        'performance_btn': '📊 عملکرد',
        'history_btn': '📜 تاریخچه',
        'price_btn': '💰 قیمت لحظه‌ای',
        'vip_btn': '💎 VIP',
        'referral_btn': '👥 رفرال',
        'settings_btn': '⚙️ تنظیمات',
        'support_btn': '🆘 پشتیبانی'
    }
    buttons = {}
    for key, default in default_buttons.items():
        custom = get_setting(f'button_{key}')
        buttons[key] = custom if custom else default
    return buttons

# ============ تنظیم سخت‌گیری استراتژی ============
def set_strategy_strictness(strategy_id, value):
    """تنظیم سخت‌گیری استراتژی"""
    from database import set_strategy_setting
    try:
        value = int(value)
        if 0 <= value <= 100:
            set_strategy_setting(strategy_id, "strictness", value)
            return f"✅ سخت‌گیری استراتژی به {value}% تغییر کرد."
        return "❌ عدد باید بین ۰ تا ۱۰۰ باشد."
    except:
        return "❌ لطفاً یک عدد معتبر وارد کنید."

# ============ بکتست ============
def run_backtest():
    """اجرای بکتست"""
    from database import get_setting
    from datetime import datetime, timedelta
    import pandas as pd
    from market import get_gold_candles
    from strategy_registry import get_strategy
    from signals import create_signal
    
    start_str = get_setting('backtest_start')
    end_str = get_setting('backtest_end')
    
    if not start_str or not end_str:
        return "❌ ابتدا بازه زمانی بکتست را تنظیم کنید."
    
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_str, '%Y-%m-%d')
    except:
        return "❌ فرمت تاریخ اشتباه است."
    
    # ===== دریافت دیتا برای بازه =====
    try:
        # دریافت دیتای روزانه از Twelve Data
        import requests
        import os
        TWELVE_DATA_KEY = os.getenv("TWELVE_DATA")
        
        if TWELVE_DATA_KEY:
            url = "https://api.twelvedata.com/time_series"
            params = {
                "symbol": "XAU/USD",
                "interval": "1day",
                "start_date": start_str,
                "end_date": end_str,
                "apikey": TWELVE_DATA_KEY,
                "format": "json"
            }
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if "values" in data and len(data["values"]) > 0:
                df_data = []
                for candle in data["values"]:
                    df_data.append({
                        'Date': pd.to_datetime(candle['datetime']),
                        'Open': float(candle['open']),
                        'High': float(candle['high']),
                        'Low': float(candle['low']),
                        'Close': float(candle['close']),
                        'Volume': int(candle.get('volume', 0))
                    })
                df = pd.DataFrame(df_data)
                df = df.set_index('Date')
                df = df.sort_index()
            else:
                return "❌ دیتایی برای این بازه پیدا نشد."
        else:
            return "❌ کلید Twelve Data تنظیم نشده است."
        
        # ===== اجرای بکتست =====
        total_signals = 0
        tp_count = 0
        sl_count = 0
        
        # گرفتن تنظیمات RR
        rr_ratio = float(get_setting('rr_ratio') or '2')
        
        # تحلیل کندل به کندل
        for i in range(20, len(df)):
            df_slice = df.iloc[:i+1]
            signal, analysis = create_signal(df_slice, 'surpri3e')
            
            if signal:
                total_signals += 1
                # شبیه‌سازی نتیجه
                entry = signal['entry']
                sl = signal['sl']
                tp = signal['tp']
                close = df.iloc[i]['Close']
                
                if signal['direction'] == 'BUY':
                    if close >= tp:
                        tp_count += 1
                    elif close <= sl:
                        sl_count += 1
                else:  # SELL
                    if close <= tp:
                        tp_count += 1
                    elif close >= sl:
                        sl_count += 1
        
        # محاسبه وین‌ریت
        winrate = round((tp_count / total_signals) * 100, 2) if total_signals > 0 else 0
        
        return f"""
📊 **نتیجه بکتست Surpri3e Strategy**

📅 **بازه زمانی:** {start_str} تا {end_str}
📈 **کل سیگنال‌ها:** {total_signals}
✅ **TP:** {tp_count}
❌ **SL:** {sl_count}
🎯 **وین‌ریت:** {winrate}%
🎯 **نسبت RR:** 1:{rr_ratio}
📊 **مجموع سود:** {tp_count * rr_ratio - sl_count} R
        """
        
    except Exception as e:
        return f"❌ خطا در اجرای بکتست: {str(e)}"

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
