import json
import os

SETTINGS_FILE = "settings.json"

def init_settings():
    if not os.path.exists(SETTINGS_FILE):
        default_settings = {
            "default_timeframe": "5min",
            "alert": True,
            "status": True,
            "signal_enabled": True,
            "channel_locked": False,
            "send_chart": False
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(default_settings, f, indent=2)

def get_settings():
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
