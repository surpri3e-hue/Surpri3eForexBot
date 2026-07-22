# ============================================================
# 📁 strategies/risk_common.py
# 📌 توابع مشترک محاسبه‌ی ریسک بین همه‌ی استراتژی‌ها.
#
# ⚠️ تاریخچه‌ی تغییرات:
# ابتدا فاصله‌ی SL/TP بر اساس ATR (نوسان واقعی کندل‌ها) بود. سپس طبق
# یک تصمیم موقت، به یک فاصله‌ی پیپ ثابت و سراسری تغییر کرد. اما این باعث
# شد کاربران پشت‌سرهم استاپ بخورند - چون در بازارهای پرنوسان (که طلا اغلب
# همینه)، نوسان طبیعی قیمت به‌راحتی از فاصله‌ی ثابت بیشتر می‌شد و حتی
# سیگنال‌های با جهت درست هم با یک نوسان طبیعی (نه برگشت واقعی روند)
# استاپ می‌خوردند.
#
# ✅ راه‌حل نهایی: برگشت کامل به محاسبه‌ی خودکار بر اساس ATR - فاصله‌ی
# استاپ همیشه متناسب با نوسان واقعی همون لحظه‌ی بازار تنظیم می‌شه، نه یک
# عدد ثابت. دیگه هیچ تنظیم دستی پیپ از پنل ادمین وجود نداره.
# ============================================================

import numpy as np

ATR_PERIOD = 14                 # تعداد کندل برای محاسبه‌ی میانگین ATR (استاندارد صنعتی)
MIN_RISK_ATR_MULTIPLIER = 0.5   # کف ریسک: حداقل نصف ATR
MAX_RISK_ATR_MULTIPLIER = 4.0   # سقف ریسک: حداکثر ۴ برابر ATR
SL_BUFFER_ATR_MULTIPLIER = 0.15  # فاصله‌ی اطمینان اضافه از خودِ نقطه‌ی pivot/sweep

# ===== fallback در صورتی که ATR قابل محاسبه نباشه (دیتای خیلی کوتاه) =====
FALLBACK_MIN_RISK_PERCENT = 0.0005
FALLBACK_MAX_RISK_PERCENT = 0.02
FALLBACK_SL_BUFFER_PERCENT = 0.0002


def calculate_atr(df, period=ATR_PERIOD):
    """
    محاسبه‌ی Average True Range روی دیتافریم کندلی.

    True Range هر کندل = بزرگترین مقدار از سه حالت:
      1. High - Low (دامنه‌ی خودِ کندل)
      2. |High - Close قبلی|
      3. |Low - Close قبلی|

    ATR = میانگین متحرک True Range روی `period` کندل اخیر - این معیار
    مستقیماً نوسان واقعی بازار رو تو همون لحظه و همون نماد نشون می‌ده.

    خروجی: عدد ATR (float) یا None اگه دیتا برای محاسبه کافی نباشه.
    """
    if df is None or len(df) < period + 1:
        return None

    high = df['High'].values
    low = df['Low'].values
    close = df['Close'].values

    true_ranges = []
    for i in range(1, len(df)):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        true_ranges.append(max(hl, hc, lc))

    if len(true_ranges) < period:
        return None

    recent_tr = true_ranges[-period:]
    atr = float(np.mean(recent_tr))
    return atr if atr > 0 else None


def get_stop_distance(df, entry_price, symbol='XAU/USD'):
    """
    فاصله‌ی استاپ (Entry تا SL) رو بر اساس نوسان واقعی بازار (ATR)
    محاسبه می‌کنه - خودکار با هر نماد، هر تایم‌فریم، و هر شرایط بازاری
    (آرام یا پرنوسان) سازگار می‌شه.

    خروجی: (risk, sl_buffer) - هر دو بر حسب واحد قیمتی (دلار)
        risk: فاصله‌ی اصلی بین Entry و SL
        sl_buffer: فاصله‌ی اطمینان اضافه (برای گذاشتن SL کمی پشت‌تر از
                   نقطه‌ی pivot/sweep، نه دقیقاً رویش)
    """
    atr = calculate_atr(df)

    if atr is not None:
        risk = max(atr * MIN_RISK_ATR_MULTIPLIER, min(atr * MAX_RISK_ATR_MULTIPLIER, atr * 1.5))
        sl_buffer = atr * SL_BUFFER_ATR_MULTIPLIER
    else:
        # ===== fallback نادر: دیتای کافی برای ATR نیست =====
        risk = entry_price * FALLBACK_MIN_RISK_PERCENT
        sl_buffer = entry_price * FALLBACK_SL_BUFFER_PERCENT

    return risk, sl_buffer

