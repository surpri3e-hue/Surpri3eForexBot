from settings import get_setting, set_setting


def is_locked():
    return get_setting("channel_lock") == "ON"



def get_channel():

    return get_setting(
        "channel_id"
    )



def toggle_lock():

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
