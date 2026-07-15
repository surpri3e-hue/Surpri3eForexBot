import numpy as np
from database import get_setting

def ict_analysis_with_explanation(df):
    try:
        if df is None or len(df) < 10:
            return None, None

        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values

        current = close[-1]
        prev = close[-2]

        ma5 = np.mean(close[-5:])
        ma10 = np.mean(close[-10:]) if len(close) >= 10 else ma5

        reasons = []
        score = 0
        direction = None

        if current > ma5 and ma5 > ma10:
            direction = "BUY"
            reasons.append("شکست سقف قبلی (BOS UP)")
            reasons.append("میانگین متحرک صعودی")
            score += 40
        elif current < ma5 and ma5 < ma10:
            direction = "SELL"
            reasons.append("شکست کف قبلی (BOS DOWN)")
            reasons.append("میانگین متحرک نزولی")
            score += 40
        else:
            price_change = ((current - prev) / prev) * 100
            if price_change > 0.05:
                direction = "BUY"
                reasons.append("افزایش قیمت لحظه‌ای")
                score += 30
            elif price_change < -0.05:
                direction = "SELL"
                reasons.append("کاهش قیمت لحظه‌ای")
                score += 30
            else:
                return None, None

        # ===== دریافت RR از تنظیمات =====
        rr_ratio = float(get_setting('rr_ratio') or '2')
        
        # ===== محاسبه Entry/SL/TP با RR متغیر =====
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

        recent_high = max(high[-5:])
        recent_low = min(low[-5:])

        if direction == "BUY" and current < recent_low + 2:
            reasons.append(f"نزدیک به ناحیه تقاضا در {recent_low:.2f}")
            score += 25
        elif direction == "SELL" and current > recent_high - 2:
            reasons.append(f"نزدیک به ناحیه عرضه در {recent_high:.2f}")
            score += 25

        signal = {
            'direction': direction,
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'score': min(score, 100)
        }

        analysis = {
            'reasons': reasons,
            'score': min(score, 100)
        }

        return signal, analysis

    except Exception as e:
        print(f"ICT Error: {e}")
        return None, None

def create_signal(df=None, analysis=None):
    if analysis and isinstance(analysis, dict):
        return {
            'direction': analysis.get('direction', 'BUY'),
            'entry': analysis.get('entry', 0),
            'sl': analysis.get('sl', 0),
            'tp': analysis.get('tp', 0),
            'score': analysis.get('score', 70)
        }
    
    return {
        'direction': 'BUY',
        'entry': 0,
        'sl': 0,
        'tp': 0,
        'score': 70
    }
