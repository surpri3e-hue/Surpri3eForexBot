from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from settings import (
    get_setting,
    set_setting
)


def settings_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "🧠 AI Settings",
                callback_data="ai_settings"
            )
        ],

        [
            InlineKeyboardButton(
                "🔒 Channel Lock",
                callback_data="channel_lock"
            )
        ],

        [
            InlineKeyboardButton(
                "🚀 Signal Control",
                callback_data="signal_control"
            )
        ],

        [
            InlineKeyboardButton(
                "⚙️ General",
                callback_data="general_settings"
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="admin_back"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)





def ai_settings_text():

    return f"""
🧠 AI SETTINGS


Mode:
{get_setting("ai_mode")}


Minimum Score:
{get_setting("minimum_score")}


FVG:
{get_setting("fvg_filter")}


Liquidity:
{get_setting("liquidity_filter")}


BOS:
{get_setting("bos_filter")}
"""





def ai_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "🟢 Safe",
                callback_data="ai_safe"
            ),

            InlineKeyboardButton(
                "🟡 Normal",
                callback_data="ai_normal"
            ),

            InlineKeyboardButton(
                "🔴 Aggressive",
                callback_data="ai_aggressive"
            )
        ],


        [
            InlineKeyboardButton(
                "➕ Score",
                callback_data="score_up"
            ),

            InlineKeyboardButton(
                "➖ Score",
                callback_data="score_down"
            )
        ],


        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="admin_settings"
            )
        ]

    ]


    return InlineKeyboardMarkup(keyboard)





def channel_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "🟢 ON/OFF",
                callback_data="toggle_channel"
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="admin_settings"
            )
        ]

    ]


    return InlineKeyboardMarkup(keyboard)
