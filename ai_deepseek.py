import requests
import json
import os

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

def analyze_with_deepseek(df, signal, analysis):
    if not DEEPSEEK_API_KEY:
        return "⚠️ دیپ سیک فعال نیست."

    try:
        last_20 = df.tail(20)

        data_for_ai = {
            "نماد": "XAU/USD",
            "قیمت فعلی": round(df['Close'].iloc[-1], 2),
            "بیشترین": round(df['High'].max(), 2),
            "کمترین": round(df['Low'].min(), 2),
            "جهت سیگنال": signal.get('direction'),
            "ورود": signal.get('entry'),
            "حد ضرر": signal.get('sl'),
            "حد سود": signal.get('tp')
        }

        prompt = f"""
داده‌های زیر را تحلیل کن:

{json.dumps(data_for_ai, indent=2, ensure_ascii=False)}

۱. روند بازار صعودی است یا نزولی؟
۲. سیگنال {signal.get('direction')} منطقی است؟
۳. احتمال موفقیت را به درصد بگو.

پاسخ مختصر و مفید باشد.
"""

        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500
        }

        response = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return f"⚠️ خطا: {response.status_code}"

    except Exception as e:
        return f"⚠️ خطا: {str(e)}"

async def chat_with_deepseek(question):
    if not DEEPSEEK_API_KEY:
        return "⚠️ دیپ سیک فعال نیست."

    try:
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": question}],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        response = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return f"⚠️ خطا: {response.status_code}"

    except Exception as e:
        return f"⚠️ خطا: {str(e)}"
