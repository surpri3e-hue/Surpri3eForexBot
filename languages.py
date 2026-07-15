# languages.py

LANGUAGES = {
    'fa': {
        'name': 'فارسی',
        # ===== مراحل اولیه =====
        'select_style': '📊 **سبک معاملاتی خود را انتخاب کنید:**',
        'select_timeframe': '⏱️ **تایم‌فریم را انتخاب کنید:**',
        'select_rr': '🎯 **نسبت ریسک به ریوارد (RR) را انتخاب کنید:**',
        
        # ===== دکمه‌های تایم‌فریم =====
        'tf_1min': '1 دقیقه',
        'tf_5min': '5 دقیقه',
        'tf_15min': '15 دقیقه',
        'tf_1h': '1 ساعت',
        'tf_4h': '4 ساعت',
        'tf_1d': '1 روز',
        
        # ===== دکمه‌های اصلی کاربر =====
        'signal_btn': '🚨 دریافت سیگنال',
        'performance_btn': '📊 عملکرد',
        'history_btn': '📜 تاریخچه',
        'price_btn': '💰 قیمت لحظه‌ای',
        'vip_btn': '💎 VIP',
        'referral_btn': '👥 رفرال',
        'settings_btn': '⚙️ تنظیمات',
        'support_btn': '🆘 پشتیبانی',
        'back_btn': '🔙 برگشت',
        'copy_link': '📤 کپی لینک',
        
        # ===== دکمه‌های نتیجه سیگنال =====
        'tp_btn': '✅ TP HIT',
        'sl_btn': '❌ SL HIT',
        'cancel_btn': '🚫 CANCEL',
        
        # ===== متن‌های سیگنال =====
        'signal_title': 'سیگنال جدید',
        'style_label': 'سبک',
        'direction_label': 'جهت',
        'entry_label': 'ورود',
        'sl_label': 'حد ضرر',
        'tp_label': 'حد سود',
        'rr_label': 'نسبت RR',
        'reasons_label': 'دلایل',
        'timeframe_label': 'تایم‌فریم',
        'price_label': 'قیمت لحظه‌ای',
        'time_label': 'زمان تهران',
        'result_label': 'نتیجه معامله را انتخاب کنید',
        
        # ===== پیام‌های وضعیت =====
        'tp_registered': '✅ **TP ثبت شد**\n\nبرای ادامه از دکمه‌های زیر استفاده کنید:',
        'sl_registered': '❌ **SL ثبت شد**\n\nبرای ادامه از دکمه‌های زیر استفاده کنید:',
        'canceled': '🚫 **سیگنال لغو شد**\n\nبرای ادامه از دکمه‌های زیر استفاده کنید:',
        'no_signal': '❌ **سیگنالی پیدا نشد**',
        'error': 'خطا',
        'welcome_back': '🤖 **به پنل خوش آمدید**',
        'fetching_price': '💰 **در حال دریافت قیمت...**',
        'price_result': '💰 **قیمت لحظه‌ای طلا**\n\n📊 XAU/USD\n\n💵 قیمت: {price:.2f} USD\n🕐 زمان تهران: {time}',
        'price_error': '❌ **خطا در دریافت قیمت**\n\nلطفاً دوباره تلاش کنید.',
        'signal_disabled': '⛔ **سیگنال‌دهی غیرفعال است.**',
        'no_signals_left': '❌ **تعداد سیگنال روزانه شما تمام شده!**\nصبر کنید تا فردا یا از طریق رفرال افزایش دهید.',
        'analyzing': '🔍 **در حال تحلیل ({timeframe})...**',
        'use_buttons': '❌ **لطفاً از دکمه‌ها استفاده کنید!**',
        
        # ===== عملکرد و تاریخچه =====
        'performance_text': '📊 **آمار عملکرد**\n\n📈 **کل معاملات:** {total}\n✅ **برنده:** {wins}\n❌ **بازنده:** {losses}\n🎯 **نرخ موفقیت:** {winrate}%\n\n📊 **سیگنال باقی‌مانده امروز:** {left}',
        'history_title': '📜 **تاریخچه معاملات:**',
        'no_history': '📭 **هنوز معامله‌ای ندارید!**',
        
        # ===== VIP و تنظیمات =====
        'vip_text': '💎 **پنل VIP**\n\n✅ **سیگنال‌های ویژه**\n✅ **آنالیز پیشرفته**\n✅ **پشتیبانی اختصاصی**\n\n👤 @RealSurprise',
        'settings_text': '⚙️ **تنظیمات**\n\n🔹 **تایم‌فریم:** {timeframe}\n🔹 **وضعیت:** {status}\n🔹 **RR:** 1:{rr}\n🔹 **سبک:** {style}\n🔹 **زبان:** {lang}',
        'online': 'آنلاین',
        'offline': 'آفلاین',
        
        # ===== رفرال =====
        'referral_text': '👥 **سیستم رفرال**\n\nلینک رفرال شما:\n`{link}`\n\nبه ازای هر ۵ رفرال، ۱ سیگنال اضافی دریافت میکنید.',
        
        # ===== پشتیبانی =====
        'support_text': '🆘 **پشتیبانی**\n\n👤 **ایدی:** {support}\n⏰ **ساعت پاسخگویی:** ۲۴ ساعته',
        
        # ===== دکمه‌های ادمین =====
        'dashboard_btn': '📊 Dashboard',
        'users_btn': '👥 Users',
        'analytics_btn': '📈 Analytics',
        'set_daily_signal_btn': '📊 Set Daily Signal',
        'set_rr_btn': '🎯 Set RR Ratio',
        'set_timeframe_btn': '⏱️ Set Timeframe',
        'referral_bonus_btn': '👥 Referral Bonus',
        'referral_threshold_btn': '🎯 Referral Threshold',
        'reset_signals_btn': '🔄 Reset Signals',
        'bot_lock_btn': '🔒 Bot Lock',
        'signal_control_btn': '🚀 Signal Control',
        'channel_lock_btn': '🔒 Channel Lock',
        'vip_user_btn': '👑 VIP User',
        'delete_user_btn': '🗑️ Delete User',
        'broadcast_btn': '📢 Broadcast',
        'reports_btn': '📊 Reports'
    },
    
    'en': {
        'name': 'English',
        # ===== مراحل اولیه =====
        'select_style': '📊 **Select your trading style:**',
        'select_timeframe': '⏱️ **Select timeframe:**',
        'select_rr': '🎯 **Select Risk/Reward Ratio (RR):**',
        
        # ===== دکمه‌های تایم‌فریم =====
        'tf_1min': '1 min',
        'tf_5min': '5 min',
        'tf_15min': '15 min',
        'tf_1h': '1 hour',
        'tf_4h': '4 hours',
        'tf_1d': '1 day',
        
        # ===== دکمه‌های اصلی کاربر =====
        'signal_btn': '🚨 Get Signal',
        'performance_btn': '📊 Performance',
        'history_btn': '📜 History',
        'price_btn': '💰 Live Price',
        'vip_btn': '💎 VIP',
        'referral_btn': '👥 Referral',
        'settings_btn': '⚙️ Settings',
        'support_btn': '🆘 Support',
        'back_btn': '🔙 Back',
        'copy_link': '📤 Copy Link',
        
        # ===== دکمه‌های نتیجه سیگنال =====
        'tp_btn': '✅ TP HIT',
        'sl_btn': '❌ SL HIT',
        'cancel_btn': '🚫 CANCEL',
        
        # ===== متن‌های سیگنال =====
        'signal_title': 'New Signal',
        'style_label': 'Style',
        'direction_label': 'Direction',
        'entry_label': 'Entry',
        'sl_label': 'Stop Loss',
        'tp_label': 'Take Profit',
        'rr_label': 'RR Ratio',
        'reasons_label': 'Reasons',
        'timeframe_label': 'Timeframe',
        'price_label': 'Live Price',
        'time_label': 'Tehran Time',
        'result_label': 'Select trade result',
        
        # ===== پیام‌های وضعیت =====
        'tp_registered': '✅ **TP registered**\n\nUse the buttons below to continue:',
        'sl_registered': '❌ **SL registered**\n\nUse the buttons below to continue:',
        'canceled': '🚫 **Signal canceled**\n\nUse the buttons below to continue:',
        'no_signal': '❌ **No signal found**',
        'error': 'Error',
        'welcome_back': '🤖 **Welcome back**',
        'fetching_price': '💰 **Fetching price...**',
        'price_result': '💰 **Live Gold Price**\n\n📊 XAU/USD\n\n💵 Price: {price:.2f} USD\n🕐 Time: {time}',
        'price_error': '❌ **Error fetching price**\n\nPlease try again.',
        'signal_disabled': '⛔ **Signal disabled.**',
        'no_signals_left': '❌ **Daily signal limit reached!**\nWait until tomorrow or increase via referrals.',
        'analyzing': '🔍 **Analyzing ({timeframe})...**',
        'use_buttons': '❌ **Please use the buttons!**',
        
        # ===== عملکرد و تاریخچه =====
        'performance_text': '📊 **Performance**\n\n📈 **Total:** {total}\n✅ **Wins:** {wins}\n❌ **Losses:** {losses}\n🎯 **Winrate:** {winrate}%\n\n📊 **Left today:** {left}',
        'history_title': '📜 **Trade History:**',
        'no_history': '📭 **No trades yet!**',
        
        # ===== VIP و تنظیمات =====
        'vip_text': '💎 **VIP Panel**\n\n✅ **Special Signals**\n✅ **Advanced Analysis**\n✅ **Dedicated Support**\n\n👤 @RealSurprise',
        'settings_text': '⚙️ **Settings**\n\n🔹 **Timeframe:** {timeframe}\n🔹 **Status:** {status}\n🔹 **RR:** 1:{rr}\n🔹 **Style:** {style}\n🔹 **Language:** {lang}',
        'online': 'Online',
        'offline': 'Offline',
        
        # ===== رفرال =====
        'referral_text': '👥 **Referral System**\n\nYour referral link:\n`{link}`\n\nFor every 5 referrals, you get 1 extra signal.',
        
        # ===== پشتیبانی =====
        'support_text': '🆘 **Support**\n\n👤 **ID:** {support}\n⏰ **Response time:** 24/7',
        
        # ===== دکمه‌های ادمین =====
        'dashboard_btn': '📊 Dashboard',
        'users_btn': '👥 Users',
        'analytics_btn': '📈 Analytics',
        'set_daily_signal_btn': '📊 Set Daily Signal',
        'set_rr_btn': '🎯 Set RR Ratio',
        'set_timeframe_btn': '⏱️ Set Timeframe',
        'referral_bonus_btn': '👥 Referral Bonus',
        'referral_threshold_btn': '🎯 Referral Threshold',
        'reset_signals_btn': '🔄 Reset Signals',
        'bot_lock_btn': '🔒 Bot Lock',
        'signal_control_btn': '🚀 Signal Control',
        'channel_lock_btn': '🔒 Channel Lock',
        'vip_user_btn': '👑 VIP User',
        'delete_user_btn': '🗑️ Delete User',
        'broadcast_btn': '📢 Broadcast',
        'reports_btn': '📊 Reports'
    },
    
    'ru': {
        'name': 'Русский',
        # ===== مراحل اولیه =====
        'select_style': '📊 **Выберите стиль торговли:**',
        'select_timeframe': '⏱️ **Выберите таймфрейм:**',
        'select_rr': '🎯 **Выберите соотношение Риск/Прибыль (RR):**',
        
        # ===== دکمه‌های تایم‌فریم =====
        'tf_1min': '1 минута',
        'tf_5min': '5 минут',
        'tf_15min': '15 минут',
        'tf_1h': '1 час',
        'tf_4h': '4 часа',
        'tf_1d': '1 день',
        
        # ===== دکمه‌های اصلی کاربر =====
        'signal_btn': '🚨 Получить сигнал',
        'performance_btn': '📊 Производительность',
        'history_btn': '📜 История',
        'price_btn': '💰 Цена',
        'vip_btn': '💎 VIP',
        'referral_btn': '👥 Рефералы',
        'settings_btn': '⚙️ Настройки',
        'support_btn': '🆘 Поддержка',
        'back_btn': '🔙 Назад',
        'copy_link': '📤 Копировать ссылку',
        
        # ===== دکمه‌های نتیجه سیگنال =====
        'tp_btn': '✅ TP HIT',
        'sl_btn': '❌ SL HIT',
        'cancel_btn': '🚫 ОТМЕНА',
        
        # ===== متن‌های سیگنال =====
        'signal_title': 'Новый сигнал',
        'style_label': 'Стиль',
        'direction_label': 'Направление',
        'entry_label': 'Вход',
        'sl_label': 'Стоп-лосс',
        'tp_label': 'Тейк-профит',
        'rr_label': 'Соотношение RR',
        'reasons_label': 'Причины',
        'timeframe_label': 'Таймфрейм',
        'price_label': 'Цена',
        'time_label': 'Время Тегеран',
        'result_label': 'Выберите результат сделки',
        
        # ===== پیام‌های وضعیت =====
        'tp_registered': '✅ **TP зарегистрирован**\n\nИспользуйте кнопки ниже для продолжения:',
        'sl_registered': '❌ **SL зарегистрирован**\n\nИспользуйте кнопки ниже для продолжения:',
        'canceled': '🚫 **Сигнал отменён**\n\nИспользуйте кнопки ниже для продолжения:',
        'no_signal': '❌ **Сигнал не найден**',
        'error': 'Ошибка',
        'welcome_back': '🤖 **Добро пожаловать**',
        'fetching_price': '💰 **Получение цены...**',
        'price_result': '💰 **Текущая цена золота**\n\n📊 XAU/USD\n\n💵 Цена: {price:.2f} USD\n🕐 Время: {time}',
        'price_error': '❌ **Ошибка получения цены**\n\nПожалуйста, попробуйте снова.',
        'signal_disabled': '⛔ **Сигналы отключены.**',
        'no_signals_left': '❌ **Дневной лимит сигналов исчерпан!**\nПодождите до завтра или увеличьте через рефералов.',
        'analyzing': '🔍 **Анализ ({timeframe})...**',
        'use_buttons': '❌ **Пожалуйста, используйте кнопки!**',
        
        # ===== عملکرد و تاریخچه =====
        'performance_text': '📊 **Производительность**\n\n📈 **Всего:** {total}\n✅ **Выигрыши:** {wins}\n❌ **Проигрыши:** {losses}\n🎯 **Процент успеха:** {winrate}%\n\n📊 **Осталось сегодня:** {left}',
        'history_title': '📜 **История сделок:**',
        'no_history': '📭 **Нет сделок!**',
        
        # ===== VIP و تنظیمات =====
        'vip_text': '💎 **VIP панель**\n\n✅ **Специальные сигналы**\n✅ **Расширенный анализ**\n✅ **Поддержка**\n\n👤 @RealSurprise',
        'settings_text': '⚙️ **Настройки**\n\n🔹 **Таймфрейм:** {timeframe}\n🔹 **Статус:** {status}\n🔹 **RR:** 1:{rr}\n🔹 **Стиль:** {style}\n🔹 **Язык:** {lang}',
        'online': 'Онлайн',
        'offline': 'Офлайн',
        
        # ===== رفرال =====
        'referral_text': '👥 **Реферальная система**\n\nВаша ссылка:\n`{link}`\n\nЗа каждые 5 рефералов вы получаете 1 дополнительный сигнал.',
        
        # ===== پشتیبانی =====
        'support_text': '🆘 **Поддержка**\n\n👤 **ID:** {support}\n⏰ **Время ответа:** 24/7',
        
        # ===== دکمه‌های ادمین =====
        'dashboard_btn': '📊 Dashboard',
        'users_btn': '👥 Users',
        'analytics_btn': '📈 Analytics',
        'set_daily_signal_btn': '📊 Set Daily Signal',
        'set_rr_btn': '🎯 Set RR Ratio',
        'set_timeframe_btn': '⏱️ Set Timeframe',
        'referral_bonus_btn': '👥 Referral Bonus',
        'referral_threshold_btn': '🎯 Referral Threshold',
        'reset_signals_btn': '🔄 Reset Signals',
        'bot_lock_btn': '🔒 Bot Lock',
        'signal_control_btn': '🚀 Signal Control',
        'channel_lock_btn': '🔒 Channel Lock',
        'vip_user_btn': '👑 VIP User',
        'delete_user_btn': '🗑️ Delete User',
        'broadcast_btn': '📢 Broadcast',
        'reports_btn': '📊 Reports'
    },
    
    'ar': {
        'name': 'العربية',
        # ===== مراحل اولیه =====
        'select_style': '📊 **اختر نمط التداول الخاص بك:**',
        'select_timeframe': '⏱️ **اختر الإطار الزمني:**',
        'select_rr': '🎯 **اختر نسبة المخاطرة/المكافأة (RR):**',
        
        # ===== دکمه‌های تایم‌فریم =====
        'tf_1min': 'دقيقة 1',
        'tf_5min': 'دقائق 5',
        'tf_15min': 'دقائق 15',
        'tf_1h': 'ساعة 1',
        'tf_4h': 'ساعات 4',
        'tf_1d': 'يوم 1',
        
        # ===== دکمه‌های اصلی کاربر =====
        'signal_btn': '🚨 الحصول على إشارة',
        'performance_btn': '📊 الأداء',
        'history_btn': '📜 التاريخ',
        'price_btn': '💰 السعر اللحظي',
        'vip_btn': '💎 VIP',
        'referral_btn': '👥 الإحالة',
        'settings_btn': '⚙️ الإعدادات',
        'support_btn': '🆘 الدعم',
        'back_btn': '🔙 رجوع',
        'copy_link': '📤 نسخ الرابط',
        
        # ===== دکمه‌های نتیجه سیگنال =====
        'tp_btn': '✅ TP HIT',
        'sl_btn': '❌ SL HIT',
        'cancel_btn': '🚫 إلغاء',
        
        # ===== متن‌های سیگنال =====
        'signal_title': 'إشارة جديدة',
        'style_label': 'النمط',
        'direction_label': 'الاتجاه',
        'entry_label': 'الدخول',
        'sl_label': 'وقف الخسارة',
        'tp_label': 'جني الأرباح',
        'rr_label': 'نسبة RR',
        'reasons_label': 'الأسباب',
        'timeframe_label': 'الإطار الزمني',
        'price_label': 'السعر اللحظي',
        'time_label': 'توقيت طهران',
        'result_label': 'اختر نتيجة الصفقة',
        
        # ===== پیام‌های وضعیت =====
        'tp_registered': '✅ **تم تسجيل TP**\n\nاستخدم الأزرار أدناه للمتابعة:',
        'sl_registered': '❌ **تم تسجيل SL**\n\nاستخدم الأزرار أدناه للمتابعة:',
        'canceled': '🚫 **تم إلغاء الإشارة**\n\nاستخدم الأزرار أدناه للمتابعة:',
        'no_signal': '❌ **لم يتم العثور على إشارة**',
        'error': 'خطأ',
        'welcome_back': '🤖 **مرحباً بك**',
        'fetching_price': '💰 **جاري الحصول على السعر...**',
        'price_result': '💰 **سعر الذهب اللحظي**\n\n📊 XAU/USD\n\n💵 السعر: {price:.2f} USD\n🕐 الوقت: {time}',
        'price_error': '❌ **خطأ في الحصول على السعر**\n\nيرجى المحاولة مرة أخرى.',
        'signal_disabled': '⛔ **الإشارات معطلة.**',
        'no_signals_left': '❌ **تم الوصول إلى الحد اليومي للإشارات!**\nانتظر حتى الغد أو قم بالزيادة عبر الإحالات.',
        'analyzing': '🔍 **جاري التحليل ({timeframe})...**',
        'use_buttons': '❌ **يرجى استخدام الأزرار!**',
        
        # ===== عملکرد و تاریخچه =====
        'performance_text': '📊 **الأداء**\n\n📈 **الإجمالي:** {total}\n✅ **الفوز:** {wins}\n❌ **الخسارة:** {losses}\n🎯 **نسبة النجاح:** {winrate}%\n\n📊 **المتبقي اليوم:** {left}',
        'history_title': '📜 **تاريخ الصفقات:**',
        'no_history': '📭 **لا توجد صفقات بعد!**',
        
        # ===== VIP و تنظیمات =====
        'vip_text': '💎 **لوحة VIP**\n\n✅ **إشارات خاصة**\n✅ **تحليل متقدم**\n✅ **دعم مخصص**\n\n👤 @RealSurprise',
        'settings_text': '⚙️ **الإعدادات**\n\n🔹 **الإطار الزمني:** {timeframe}\n🔹 **الحالة:** {status}\n🔹 **RR:** 1:{rr}\n🔹 **النمط:** {style}\n🔹 **اللغة:** {lang}',
        'online': 'متصل',
        'offline': 'غير متصل',
        
        # ===== رفرال =====
        'referral_text': '👥 **نظام الإحالة**\n\nرابط الإحالة الخاص بك:\n`{link}`\n\nلكل 5 إحالات، تحصل على إشارة إضافية واحدة.',
        
        # ===== پشتیبانی =====
        'support_text': '🆘 **الدعم**\n\n👤 **المعرف:** {support}\n⏰ **وقت الاستجابة:** 24/7',
        
        # ===== دکمه‌های ادمین =====
        'dashboard_btn': '📊 Dashboard',
        'users_btn': '👥 Users',
        'analytics_btn': '📈 Analytics',
        'set_daily_signal_btn': '📊 Set Daily Signal',
        'set_rr_btn': '🎯 Set RR Ratio',
        'set_timeframe_btn': '⏱️ Set Timeframe',
        'referral_bonus_btn': '👥 Referral Bonus',
        'referral_threshold_btn': '🎯 Referral Threshold',
        'reset_signals_btn': '🔄 Reset Signals',
        'bot_lock_btn': '🔒 Bot Lock',
        'signal_control_btn': '🚀 Signal Control',
        'channel_lock_btn': '🔒 Channel Lock',
        'vip_user_btn': '👑 VIP User',
        'delete_user_btn': '🗑️ Delete User',
        'broadcast_btn': '📢 Broadcast',
        'reports_btn': '📊 Reports'
    }
}

def get_text(lang, key):
    """دریافت متن بر اساس زبان"""
    if lang not in LANGUAGES:
        lang = 'fa'
    return LANGUAGES[lang].get(key, key)
