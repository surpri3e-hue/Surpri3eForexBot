# ai_deepseek.py
import requests
import json
import os

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

def analyze_with_deepseek(df, signal, analysis):
    """
    ارسال دیتای چارت به دیپ سیک و دریافت نظر
    """
    if not DEEPSEEK_API_KEY:
        return "⚠️ دیپ سیک فعال نیست. لطفاً API Key را تنظیم کنید."
    
    try:
        # ===== آماده‌سازی دیتا برای دیپ سیک =====
        last_20 = df.tail(20)
        
        data_for_ai = {
            "نماد": "XAU/USD",
            "قیمت فعلی": round(df['Close'].iloc[-1], 2),
            "بیشترین قیمت": round(df['High'].max(), 2),
            "کمترین قیمت": round(df['Low'].min(), 2),
            "میانگین متحرک ۲۰": round(df['Close'].rolling(20).mean().iloc[-1], 2),
            "میانگین متحرک ۵۰": round(df['Close'].rolling(50).mean().iloc[-1], 2) if len(df) >= 50 else "ندارد",
            "RSI": calculate_rsi(df['Close']),
            "سیگنال ICT": {
                "جهت": signal.get('direction'),
                "ورود": signal.get('entry'),
                "حد ضرر": signal.get('sl'),
                "حد سود": signal.get('tp'),
                "دلایل": analysis.get('reasons', [])
            },
            "آخرین ۵ کندل": [
                {
                    "open": round(df['Open'].iloc[-i], 2),
                    "high": round(df['High'].iloc[-i], 2),
                    "low": round(df['Low'].iloc[-i], 2),
                    "close": round(df['Close'].iloc[-i], 2)
                } for i in range(1, 6)
            ]
        }
        
        # ===== ساخت پرامپت برای دیپ سیک =====
        prompt = f"""
شما یک تحلیلگر حرفه‌ای بازار طلا با سبک ICT هستید.

داده‌های زیر را تحلیل کنید:

{json.dumps(data_for_ai, indent=2, ensure_ascii=False)}

لطفاً به این سوالات پاسخ دهید:

۱. روند فعلی بازار صعودی است یا نزولی؟ چرا؟
۲. سیگنال {signal.get('direction')} که صادر شده منطقی است؟
۳. دلایل اصلی برای این سیگنال چیست؟
۴. چه عواملی ممکن است باعث شکست این سیگنال شود؟
۵. احتمال موفقیت (وین‌ریت) این سیگنال را به صورت درصد تخمین بزن.

پاسخ را به صورت زیر بنویس:

🔍 **تحلیل روند:**
[پاسخ بخش ۱]

📊 **تحلیل سیگنال:**
[پاسخ بخش ۲ و ۳]

⚠️ **هشدارها:**
[پاسخ بخش ۴]

🎯 **احتمال موفقیت:**
[پاسخ بخش ۵ به صورت عددی]

📝 **نتیجه‌گیری کلی:**
[خلاصه نهایی]
"""
        
        # ===== ارسال به دیپ سیک =====
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "شما یک تحلیلگر حرفه‌ای فارکس با سبک ICT هستید."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = requests.post(
            DEEPSEEK_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"⚠️ خطا در ارتباط با دیپ سیک: {response.status_code}"
            
    except Exception as e:
        return f"⚠️ خطا: {str(e)}"

def calculate_rsi(close, period=14):
    """
    محاسبه RSI
    """
    try:
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi.iloc[-1], 2)
    except:
        return None

def analyze_with_ict_and_ai(df, signal, analysis):
    """
    ترکیب تحلیل ICT و نظر دیپ سیک
    """
    # ===== تحلیل ICT =====
    ict_result = f"""
📊 **تحلیل ICT:**

جهت: {signal['direction']}
ورود: {signal['entry']:.2f}
حد ضرر: {signal['sl']:.2f}
حد سود: {signal['tp']:.2f}

دلایل:
{chr(10).join([f"• {r}" for r in analysis.get('reasons', ['دلیلی ثبت نشده'])])}

امتیاز: {analysis.get('score', 0)}
"""
    
    # ===== نظر دیپ سیک =====
    ai_result = analyze_with_deepseek(df, signal, analysis)
    
    # ===== ترکیب =====
    return f"""
{ict_result}

🤖 **نظر دیپ سیک:**

{ai_result}

📡 **زمان تحلیل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
