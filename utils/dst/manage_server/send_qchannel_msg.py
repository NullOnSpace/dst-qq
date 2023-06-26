import requests

import os
import sys

CWD = os.path.dirname(__file__)
if CWD not in sys.path:
    sys.path.append(CWD)
from qchannel_config import ADDRESS, GUILD_ID, CHAT_CHANNEL_ID

URL_GET_CHANNEL_LIST = "/get_guild_channel_list"
URL_SEND_GUILD_CHANNEL_MSG = "/send_guild_channel_msg"


def send_msg_to_channel(msg, room=None, gid=None, cid=None):
    CHANNEL_ROOM = {
        'chat': (GUILD_ID, CHAT_CHANNEL_ID)
    }
    params = {
        "guild_id": gid if room is None else CHANNEL_ROOM[room][0],
        "channel_id": cid if room is None else CHANNEL_ROOM[room][1],
        "message": msg,
    }
    url = "http://" + ADDRESS + URL_SEND_GUILD_CHANNEL_MSG
    try:
        res = requests.get(url, params=params)
    except requests.exceptions.ConnectionError:
        return False
    if res.status_code == 200:
        r = res.json()
        if r.get("status") and r['status'] == "ok":
            return True
    return False

if __name__ == "__main__":
    r = send_msg_to_channel("hello world", room='chat')
    print(r)