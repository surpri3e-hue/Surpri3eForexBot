from settings import get_setting, set_setting
from database import get_statistics
from users import get_users_count



def dashboard():

    stats = get_statistics()

    return f"""
📊 DASHBOARD


👥 Users:
{get_users_count()}


📈 Trades:
{stats['total']}


✅ Wins:
{stats['wins']}


❌ Loss:
{stats['losses']}


🎯 Win Rate:
{stats['winrate']}%


💰 Profit Factor:
{stats['profit_factor']}


🧠 AI:
{get_setting('ai_mode')}


🎯 Score:
{get_setting('minimum_score')}
"""





def toggle_signal():

    current = get_setting(
        "signal_status"
    )


    if current == "ON":

        set_setting(
            "signal_status",
            "OFF"
        )

        return "OFF"


    else:

        set_setting(
            "signal_status",
            "ON"
        )

        return "ON"
