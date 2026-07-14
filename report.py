from database import get_stats


def create_report():

    stats = get_stats()

    report = f"""
📊 Surpri3e Forex Bot Status

Total Signals:
{stats['total']}

✅ TP Hit:
{stats['wins']}

❌ SL Hit:
{stats['losses']}

Win Rate:
{stats['winrate']}%

Profit Factor:
{stats['profit_factor']}

RR:
1:2
"""

    return report
