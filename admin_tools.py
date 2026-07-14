from settings import get_setting, set_setting
from database import get_statistics
from users import get_users_count
from logs import get_logs





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


🚨 Signal:
{get_setting('signal_status')}


🧠 AI:
{get_setting('ai_mode')}
"""





def toggle_signal():

    current = get_setting(
        "signal_status"
    )


    new = "OFF"


    if current == "OFF":

        new = "ON"



    set_setting(
        "signal_status",
        new
    )


    return new





def toggle_channel_lock():

    current = get_setting(
        "channel_lock"
    )


    new = "OFF"


    if current == "OFF":

        new = "ON"



    set_setting(
        "channel_lock",
        new
    )


    return new





def ai_status():

    return f"""
🧠 AI SETTINGS


Mode:
{get_setting('ai_mode')}


FVG:
{get_setting('fvg_filter')}


Liquidity:
{get_setting('liquidity_filter')}


BOS:
{get_setting('bos_filter')}


Minimum Score:
{get_setting('minimum_score')}
"""





def logs_text():

    logs = get_logs()


    if not logs:

        return "📜 No Logs"



    text = "📜 LAST LOGS\n\n"


    for time, action in logs:

        text += f"🕒 {time}\n{action}\n\n"


    return text
