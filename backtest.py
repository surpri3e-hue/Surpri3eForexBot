# ============================================================
# 📁 backtest.py
# 📌 وظیفه: اجرای بک‌تست یک استراتژی روی داده‌ی تاریخی واقعی،
#          و محاسبه‌ی وین‌ریت واقعی نسبت به سیگنال‌های تولیدشده.
# 📅 ساخته‌شده: 2026-07-17
#
# ⚠️ محدودیت صادقانه: این بک‌تست ساده‌ست - هر کندل رو با دیتای
# تجمعی تا همون لحظه تحلیل می‌کنه و TP/SL رو با کندل‌های بعدی
# می‌سنجه. این looک‌فوروارد بایاس نداره، ولی spread/slippage/کارمزد
# رو در نظر نمی‌گیره، پس نتیجه‌ی واقعی معاملات زنده معمولاً
# کمی ضعیف‌تر از عدد این بک‌تسته.
# ============================================================

from market import get_historical_candles
from strategy_registry import run_strategy

# حداکثر تعداد کندل که با یک بار تحلیل، صبر می‌کنیم TP/SL بخوره
# (اگه هیچ‌کدوم نخورد، معامله رو نامشخص در نظر می‌گیریم - نه برد نه باخت)
MAX_LOOKFORWARD_BARS = 200

# حداقل تعداد کندل برای شروع تحلیل (باید با نیاز خود استراتژی هماهنگ باشه)
MIN_CANDLES_FOR_ANALYSIS = 30


def run_backtest(strategy_id, start_date, end_date, timeframe="1h"):
    """
    بک‌تست یک استراتژی رو روی بازه‌ی زمانی مشخص اجرا می‌کنه.

    خروجی: dict
        {
            'success': bool,
            'error': str (فقط اگه success=False),
            'total_signals': int,
            'tp_count': int,
            'sl_count': int,
            'undecided_count': int,  # سیگنال‌هایی که تا آخر دیتا نه TP نه SL خوردن
            'winrate': float,        # فقط از بین TP/SL (نه undecided)
            'start_date': str,
            'end_date': str,
            'timeframe': str,
        }
    """
    df = get_historical_candles(start_date, end_date, timeframe)

    if df is None or len(df) < MIN_CANDLES_FOR_ANALYSIS + 10:
        return {
            'success': False,
            'error': 'دیتای کافی برای این بازه‌ی زمانی در دسترس نیست (یا کلید Twelve Data تنظیم نشده).',
        }

    total_signals = 0
    tp_count = 0
    sl_count = 0
    undecided_count = 0

    i = MIN_CANDLES_FOR_ANALYSIS
    n = len(df)

    while i < n:
        df_slice = df.iloc[:i + 1].copy()
        df_slice.attrs['is_real_data'] = True

        signal, analysis = run_strategy(strategy_id, df_slice)

        if signal:
            total_signals += 1
            direction = signal['direction']
            sl = signal['sl']
            tp = signal['tp']

            # ===== جست‌وجوی رو به جلو برای دیدن TP یا SL کدوم اول خورده =====
            result = None
            lookforward_end = min(i + 1 + MAX_LOOKFORWARD_BARS, n)
            for j in range(i + 1, lookforward_end):
                future_high = df.iloc[j]['High']
                future_low = df.iloc[j]['Low']

                if direction == 'BUY':
                    if future_high >= tp:
                        result = 'TP'
                        break
                    if future_low <= sl:
                        result = 'SL'
                        break
                else:  # SELL
                    if future_low <= tp:
                        result = 'TP'
                        break
                    if future_high >= sl:
                        result = 'SL'
                        break

            if result == 'TP':
                tp_count += 1
            elif result == 'SL':
                sl_count += 1
            else:
                undecided_count += 1

            # بعد از یک سیگنال، به‌جای بررسی کندل بعدی بلافاصله، از انتهای
            # بازه‌ی lookforward (یا حداقل چند کندل جلوتر) ادامه می‌دیم، تا
            # یک معامله‌ی باز با معامله‌ی بعدی قاطی نشه.
            i = (i + 1 + MAX_LOOKFORWARD_BARS) if result is None else (j + 1)
        else:
            i += 1

    decided = tp_count + sl_count
    winrate = round((tp_count / decided) * 100, 2) if decided > 0 else 0

    return {
        'success': True,
        'total_signals': total_signals,
        'tp_count': tp_count,
        'sl_count': sl_count,
        'undecided_count': undecided_count,
        'winrate': winrate,
        'start_date': start_date,
        'end_date': end_date,
        'timeframe': timeframe,
    }


def format_backtest_report(result, strategy_display_name="استراتژی"):
    """نتیجه‌ی run_backtest رو به یک متن قابل‌نمایش در تلگرام تبدیل می‌کنه."""
    if not result.get('success'):
        return f"❌ **خطا در بک‌تست:**\n{result.get('error', 'خطای نامشخص')}"

    return f"""
📊 **نتیجه‌ی بک‌تست {strategy_display_name}**

📅 **بازه:** {result['start_date']} تا {result['end_date']}
⏱️ **تایم‌فریم:** {result['timeframe']}

📈 **کل سیگنال‌های تولیدشده:** {result['total_signals']}
✅ **TP خورده:** {result['tp_count']}
❌ **SL خورده:** {result['sl_count']}
⏳ **نامشخص (تا آخر داده به نتیجه نرسید):** {result['undecided_count']}

🎯 **وین‌ریت (فقط از بین TP/SL):** {result['winrate']}%

⚠️ _این بک‌تست spread، کارمزد و لغزش قیمت (slippage) را در نظر نمی‌گیرد؛ نتیجه‌ی معاملات واقعی معمولاً کمی پایین‌تر است._
"""
