# languages.py
LANGUAGES = {
    'fa': {
        'name': 'فارسی',
        'start': '🤖 به ربات سیگنال‌دهی خوش آمدید!',
        'select_style': '📊 سبک معاملاتی خود را انتخاب کنید:',
        'select_timeframe': '⏱️ تایم‌فریم را انتخاب کنید:',
        'signal_title': '🚨 سیگنال جدید',
        'direction': 'جهت',
        'entry': 'ورود',
        'sl': 'حد ضرر',
        'tp': 'حد سود',
        'reasons': 'دلایل',
        'no_signal': '❌ سیگنالی پیدا نشد',
        'error': '❌ خطا',
        'vip': '💎 پنل VIP',
        'referral': '👥 سیستم رفرال',
        'back': '🔙 برگشت',
        'settings': '⚙️ تنظیمات'
    },
    'en': {
        'name': 'English',
        'start': '🤖 Welcome to Signal Bot!',
        'select_style': '📊 Select your trading style:',
        'select_timeframe': '⏱️ Select timeframe:',
        'signal_title': '🚨 New Signal',
        'direction': 'Direction',
        'entry': 'Entry',
        'sl': 'Stop Loss',
        'tp': 'Take Profit',
        'reasons': 'Reasons',
        'no_signal': '❌ No signal found',
        'error': '❌ Error',
        'vip': '💎 VIP Panel',
        'referral': '👥 Referral System',
        'back': '🔙 Back',
        'settings': '⚙️ Settings'
    },
    'ru': {
        'name': 'Русский',
        'start': '🤖 Добро пожаловать в бот сигналов!',
        'select_style': '📊 Выберите стиль торговли:',
        'select_timeframe': '⏱️ Выберите таймфрейм:',
        'signal_title': '🚨 Новый сигнал',
        'direction': 'Направление',
        'entry': 'Вход',
        'sl': 'Стоп-лосс',
        'tp': 'Тейк-профит',
        'reasons': 'Причины',
        'no_signal': '❌ Сигнал не найден',
        'error': '❌ Ошибка',
        'vip': '💎 VIP панель',
        'referral': '👥 Реферальная система',
        'back': '🔙 Назад',
        'settings': '⚙️ Настройки'
    },
    'ar': {
        'name': 'العربية',
        'start': '🤖 مرحبا بكم في بوت الإشارات!',
        'select_style': '📊 اختر نمط التداول الخاص بك:',
        'select_timeframe': '⏱️ اختر الإطار الزمني:',
        'signal_title': '🚨 إشارة جديدة',
        'direction': 'الاتجاه',
        'entry': 'الدخول',
        'sl': 'وقف الخسارة',
        'tp': 'جني الأرباح',
        'reasons': 'الأسباب',
        'no_signal': '❌ لم يتم العثور على إشارة',
        'error': '❌ خطأ',
        'vip': '💎 لوحة VIP',
        'referral': '👥 نظام الإحالة',
        'back': '🔙 رجوع',
        'settings': '⚙️ الإعدادات'
    }
}

def get_text(lang, key):
    """دریافت متن بر اساس زبان"""
    return LANGUAGES.get(lang, LANGUAGES['fa']).get(key, key)
