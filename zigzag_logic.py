# zigzag_logic.py
import numpy as np
import pandas as pd

class ZigzagDetector:
    def __init__(self, depth=5, deviation=3, backstep=3):
        self.depth = depth
        self.deviation = deviation
        self.backstep = backstep
        self.last_pivot_price = None
        self.last_pivot_dir = 0
        self.direction = 0
        self.pivot_points = []
        self.last_signal = None  # جلوگیری از سیگنال تکراری
        self.last_signal_price = 0

    def find_pivots(self, high, low):
        """پیدا کردن قله‌ها و دره‌ها با الگوریتم زیگزاگ"""
        pivots = []
        length = len(high)

        for i in range(self.depth, length - self.depth):
            # ===== تشخیص قله =====
            is_high = True
            for j in range(1, self.depth + 1):
                if i - j < 0 or i + j >= length:
                    is_high = False
                    break
                if high[i] < high[i - j] or high[i] < high[i + j]:
                    is_high = False
                    break
                # حداقل فاصله برای جلوگیری از نویز
                if abs(high[i] - high[i - j]) < 0.5:
                    is_high = False
                    break

            # ===== تشخیص دره =====
            is_low = True
            if not is_high:
                for j in range(1, self.depth + 1):
                    if i - j < 0 or i + j >= length:
                        is_low = False
                        break
                    if low[i] > low[i - j] or low[i] > low[i + j]:
                        is_low = False
                        break
                    if abs(low[i] - low[i - j]) < 0.5:
                        is_low = False
                        break

            if is_high:
                pivots.append({'index': i, 'price': high[i], 'type': 'high'})
            elif is_low:
                pivots.append({'index': i, 'price': low[i], 'type': 'low'})

        return pivots

    def validate_signal(self, direction, price, current_price):
        """اعتبارسنجی سیگنال برای جلوگیری از نقض"""
        # جلوگیری از سیگنال تکراری در قیمت یکسان
        if self.last_signal == direction and abs(price - self.last_signal_price) < 3:
            return False

        # جلوگیری از سیگنال‌های متناقض پشت سر هم
        if self.last_signal == 'BUY' and direction == 'SELL':
            # حداقل ۵ دلار فاصله برای تغییر جهت
            if abs(current_price - self.last_signal_price) < 5:
                return False
        if self.last_signal == 'SELL' and direction == 'BUY':
            if abs(current_price - self.last_signal_price) < 5:
                return False

        return True

    def get_signal(self, df):
        """دریافت سیگنال از زیگزاگ با اعتبارسنجی"""
        if df is None or len(df) < 20:
            return None, None

        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        current_price = close[-1]

        # پیدا کردن نقاط عطف
        pivots = self.find_pivots(high, low)

        if len(pivots) < 4:
            return None, None

        # گرفتن ۴ نقطه آخر برای تحلیل دقیق‌تر
        last_four = pivots[-4:]

        # ===== تشخیص روند با استفاده از ۴ نقطه =====
        # الگوی صعودی: low → high → low (بالاتر) → high (بالاتر)
        if (last_four[0]['type'] == 'low' and
            last_four[1]['type'] == 'high' and
            last_four[2]['type'] == 'low' and
            last_four[3]['type'] == 'high'):
            
            # بررسی شکست سقف قبلی
            if last_four[3]['price'] > last_four[1]['price']:
                direction = "BUY"
                reasons = [
                    f"شکست سقف قبلی در {last_four[1]['price']:.2f}",
                    f"سقف جدید در {last_four[3]['price']:.2f}",
                    f"زیگزاگ صعودی تأیید شد",
                    f"قیمت با قدرت از {last_four[0]['price']:.2f} صعود کرده"
                ]
                
                if self.validate_signal(direction, current_price, current_price):
                    self.last_signal = direction
                    self.last_signal_price = current_price
                    return direction, reasons

        # الگوی نزولی: high → low → high (پایین‌تر) → low (پایین‌تر)
        if (last_four[0]['type'] == 'high' and
            last_four[1]['type'] == 'low' and
            last_four[2]['type'] == 'high' and
            last_four[3]['type'] == 'low'):
            
            # بررسی شکست کف قبلی
            if last_four[3]['price'] < last_four[1]['price']:
                direction = "SELL"
                reasons = [
                    f"شکست کف قبلی در {last_four[1]['price']:.2f}",
                    f"کف جدید در {last_four[3]['price']:.2f}",
                    f"زیگزاگ نزولی تأیید شد",
                    f"قیمت با قدرت از {last_four[0]['price']:.2f} نزول کرده"
                ]
                
                if self.validate_signal(direction, current_price, current_price):
                    self.last_signal = direction
                    self.last_signal_price = current_price
                    return direction, reasons

        return None, None

def get_zigzag_signal(df):
    """
    دریافت سیگنال زیگزاگ با اعتبارسنجی کامل
    """
    detector = ZigzagDetector(depth=5, deviation=3, backstep=3)
    direction, reasons = detector.get_signal(df)

    if direction is None:
        return None, None

    # ===== محاسبه Entry/SL/TP =====
    from database import get_setting
    current = df['Close'].iloc[-1]
    rr_ratio = float(get_setting('rr_ratio') or '2')
    RISK = 5.0
    REWARD = RISK * rr_ratio

    if direction == "BUY":
        entry = round(current, 2)
        sl = round(current - RISK, 2)
        tp = round(current + REWARD, 2)
    else:
        entry = round(current, 2)
        sl = round(current + RISK, 2)
        tp = round(current - REWARD, 2)

    signal = {
        'direction': direction,
        'entry': entry,
        'sl': sl,
        'tp': tp,
    }

    analysis = {
        'reasons': reasons,
        'style': 'Zigzag'
    }

    return signal, analysis
