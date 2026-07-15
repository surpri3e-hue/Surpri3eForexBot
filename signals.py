# signals.py
from ict_logic import analyze_ict
from smc_logic import analyze_smc
import numpy as np

def create_signal(df, style='ICT'):
    """
    دریافت سیگنال بر اساس سبک انتخابی
    اگر هیچ سیگنالی پیدا نشد، یک سیگنال اضطراری می‌سازد
    """
    # ===== بررسی دیتا =====
    if df is None or len(df) < 20:
        return None, None

    signal = None
    analysis = None

    # ===== انتخاب سبک =====
    if style == 'ICT':
        signal, analysis = analyze_ict(df)
    elif style == 'SMC':
        signal, analysis = analyze_smc(df)
    else:
        return None, None

    # ===== اگر سیگنال وجود نداشت، سیگنال اضطراری بساز =====
    if signal is None:
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        
        # تغییر قیمت
        price_change = ((current_price - prev_price) / prev_price) * 100
        
        # ===== تشخیص جهت بر اساس تغییر قیمت =====
        if price_change > 0:
            direction = "BUY"
            reason = f"افزایش قیمت لحظه‌ای ({price_change:.2f}%)"
        elif price_change < 0:
            direction = "SELL"
            reason = f"کاهش قیمت لحظه‌ای ({price_change:.2f}%)"
        else:
            # اگر قیمت تغییر نکرده بود
            direction = "BUY"
            reason = "قیمت ثابت - پیش‌فرض BUY"
        
        # ===== Entry/SL/TP =====
        from database import get_setting
        rr_ratio = float(get_setting('rr_ratio') or '2')
        RISK = 5.0
        REWARD = RISK * rr_ratio

        if direction == "BUY":
            entry = round(current_price, 2)
            sl = round(current_price - RISK, 2)
            tp = round(current_price + REWARD, 2)
        else:
            entry = round(current_price, 2)
            sl = round(current_price + RISK, 2)
            tp = round(current_price - REWARD, 2)

        signal = {
            'direction': direction,
            'entry': entry,
            'sl': sl,
            'tp': tp,
        }

        analysis = {
            'reasons': [f"⚠️ سیگنال اضطراری: {reason}"],
            'style': style
        }

    # ===== حذف امتیاز =====
    if 'score' in signal:
        del signal['score']
    if 'score' in analysis:
        del analysis['score']

    return signal, analysis
