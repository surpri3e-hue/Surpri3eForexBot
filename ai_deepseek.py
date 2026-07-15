import requests
import json
import os

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

# ============ بدون دیپ سیک (Fallback) ============
def get_fallback_analysis(signal, analysis):
    """تحلیل ساده بدون دیپ سیک"""
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

⚠️ **توجه:** دیپ سیک در حال حاضر در دسترس نیست.
"""

def analyze_with_deepseek(df, signal, analysis):
    """
    تحلیل با دیپ سیک (با Fallback)
    """
    if not DEEPSEEK_API_KEY:
        return get_fallback_analysis(signal, analysis)
    
    try:
        # آماده‌سازی دیتا
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

پاسخ را به صورت زیر بده:
📊 روند: [صعودی/نزولی]
🎯 تحلیل سیگنال: [منطقی است/منطقی نیست]
📈 احتمال موفقیت: [عدد]%
"""

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "شما تحلیلگر بازار طلا هستید. مختصر پاسخ دهید."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 300
        }
        
        response = requests.post(
            DEEPSEEK_URL,
            headers=headers,
            json=payload,
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        elif response.status_code == 402:
            # ارور پرداخت
            return get_fallback_analysis(signal, analysis) + "\n\n⚠️ **دیپ سیک: نیاز به شارژ حساب**"
        else:
            return get_fallback_analysis(signal, analysis)
            
    except Exception as e:
        print(f"DeepSeek error: {e}")
        return get_fallback_analysis(signal, analysis)

async def chat_with_deepseek(question):
    """
    چت با دیپ سیک (با Fallback)
    """
    if not DEEPSEEK_API_KEY:
        return "⚠️ دیپ سیک فعال نیست. لطفاً API Key را تنظیم کنید."
    
    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "شما تحلیلگر بازار طلا هستید. به فارسی پاسخ دهید."},
                {"role": "user", "content": question}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(
            DEEPSEEK_URL,
            headers=headers,
            json=payload,
            timeout=25
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        elif response.status_code == 402:
            return "⚠️ **خطای 402:** اعتبار حساب دیپ سیک تمام شده است.\n\nلطفاً حساب خود را شارژ کنید یا با ادمین تماس بگیرید.\n\n💡 ربات همچنان با تحلیل خودکار کار میکند."
        else:
            return f"⚠️ خطا در ارتباط با دیپ سیک: {response.status_code}\n\n💡 ربات با تحلیل خودکار کار میکند."
            
    except Exception as e:
        return f"⚠️ خطا: {str(e)}\n\n💡 ربات با تحلیل خودکار کار میکند."
