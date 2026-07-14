from database import get_statistics



def create_report():

    stats = get_statistics()


    return f"""
📊 Surpri3e AI Report


📌 Total Trades:
{stats['total']}


✅ Wins:
{stats['wins']}


❌ Losses:
{stats['losses']}


🎯 Win Rate:
{stats['winrate']}%


💰 Profit Factor:
{stats['profit_factor']}

"""
