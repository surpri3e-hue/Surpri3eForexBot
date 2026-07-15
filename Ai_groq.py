import requests
import json
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def analyze_with_groq(df, signal, analysis):
    """
    تحلیل با Groq (رایگان)
    """
    if not GROQ_API_KEY:
        return get_fallback_analysis(signal, analysis)
    
    try:
        current_price = df['Close'].iloc[-1]
        high_price = df['High'].max()
        low_price = df['Low'].min()
        
        data_for_ai = {
            "نماد": "XAU/USD",
            "قیمت فعلی": round(current_price, 2),
            "بیشترین قیمت": round(high_price, 2),
            "کمترین قیمت": round(low_price, 2),
            "جهت سیگنال": signal.get('direction'),
            "ورود": signal.get('entry'),
            "حد ضرر": signal.get('sl'),
            "حد سود": signal.get('tp'),
            "دلایل": analysis.get('reasons', [])
        }
        
        prompt = f"""
داده‌های زیر را تحلیل کن و پاسخ مختصر بده:

{json.dumps(data_for_ai, indent=2, ensure_ascii=False)}

۱. روند بازار صعودی است یا نزولی؟
۲. سیگنال {signal.get('direction')} منطقی است؟
۳. احتمال موفقیت را به درصد بگو.

پاسخ را به این صورت بده:
📊 روند: [صعودی/نزولی]
🎯 تحلیل سیگنال: [منطقی است/منطقی نیست]
📈 احتمال موفقیت: [عدد]%
"""

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama3-70b-8192",
            "messages": [
                {"role": "system", "content": "شما تحلیلگر بازار طلا هستید. مختصر پاسخ دهید."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 300
        }
        
        response = requests.post(
            GROQ_URL,
            headers=headers,
            json=payload,
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return get_fallback_analysis(signal, analysis)
            
    except Exception as e:
        print(f"Groq error: {e}")
        return get_fallback_analysis(signal, analysis)

async def chat_with_groq(question):
    """
    چت با Groq (رایگان)
    """
    if not GROQ_API_KEY:
        return "⚠️ Groq فعال نیست. لطفاً API Key را تنظیم کنید."
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama3-70b-8192",
            "messages": [
                {"role": "system", "content": "شما تحلیلگر بازار طلا هستید. به فارسی پاسخ دهید."},
                {"role": "user", "content": question}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(
            GROQ_URL,
            headers=headers,
            json=payload,
            timeout=25
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"⚠️ خطا در ارتباط با Groq: {response.status_code}"
            
    except Exception as e:
        return f"⚠️ خطا: {str(e)}"

def get_fallback_analysis(signal, analysis):
    """تحلیل ساده بدون API"""
    direction = signal.get('direction', 'BUY')
    entry = signal.get('entry', 0)
    sl = signal.get('sl', 0)
    tp = signal.get('tp', 0)
    
    if direction == 'BUY':
        trend = "صعودی"
        recommendation = "خرید"
    else:
        trend = "نزولی"
        recommendation = "فروش"
    
    return f"""
🔍 **تحلیل خودکار:**

📊 **روند:** {trend}
🎯 **سیگنال:** {recommendation} در قیمت {entry:.2f}
🛑 **حد ضرر:** {sl:.2f}
🎯 **حد سود:** {tp:.2f}

💡 **توضیح:**
بر اساس تحلیل ICT، {len(analysis.get('reasons', []))} دلیل برای این سیگنال وجود دارد.
"""
