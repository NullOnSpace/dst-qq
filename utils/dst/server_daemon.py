import json
import os 
import sys

CWD = os.path.dirname(__file__)
sys.path.append(CWD)
from manage_server.get_config import CLUSTER_DIR
from manage_server.parse_save import countprefab
from manage_server.get_prefab_list import PREFABS, update as update_prefabs, get_reverse_prefabs
from manage_server.manage_user import session_to_ku, ku_to_name
from manage_server.archive_cluster import zip_cluster
from manage_server.mega_backup import backup
from manage_server.edit_setting import edit as _edit_cluster, print_config
from manage_server.parse_save import get_latest_save, parse_user
from manage_server.manage_user import session_to_ku, ku_to_name

import redis

REDIS_TASK_KEY = 'DST:DAEMON:TASKS'
REDIS_TASK_RESULT_KEY_PREPEND = 'DST:DAEMON:TASK_DONE:'
REDIS_PREFABS = 'dst:data:prefabs'
REDIS_CONSOLE_COMAND = "dst:server:console:command"
REDIS_CONSOLE_COMAND_CAVE = "dst:server:console:command:cave"

DROP_COMMAND_TPL = 'local p = UserToPlayer("{ku}");if p ~= nil then p.components.inventory:DropEverything() end'
BAN_COMMAND_TPL = 'TheNet:Ban("{ku}")'
KICK_COMMAND_TPL = 'TheNet:Kick("{ku}", {seconds})'


def drop_player_everything(ku):
    r = redis.Redis(decode_responses=True)
    r.lpush(REDIS_CONSOLE_COMAND, DROP_COMMAND_TPL.format(ku=ku))
    r.lpush(REDIS_CONSOLE_COMAND_CAVE, DROP_COMMAND_TPL.format(ku=ku))
    r.close()

def ban_player(ku):
    r = redis.Redis(decode_responses=True)
    drop_player_everything(ku)
    r.lpush(REDIS_CONSOLE_COMAND, BAN_COMMAND_TPL.format(ku=ku))
    r.close()

def kick_player(ku, kick_seconds=10*60):
    r = redis.Redis(decode_responses=True)
    drop_player_everything(ku)
    r.lpush(REDIS_CONSOLE_COMAND, 
            KICK_COMMAND_TPL.format(ku=ku, seconds=kick_seconds))
    r.close()


def get_users_stat():
    # user statistics of time, prefab, is_alive
    saves = get_latest_save(user=True)
    users = saves['user']
    result = []
    for user_session, entry in users.items():
        userdata = parse_user(entry.path)
        if userdata:
            try:
                data = userdata['data']
                age = data['age']['age']
                is_alive = not data.get('is_ghost')
            except KeyError:
                continue
            else:
                ku = session_to_ku(user_session)
                username = ku_to_name(ku)
                last_login = entry.stat().st_mtime
                stat = {
                    'username': username, 'ku': ku, 
                    'age': age, 'is_alive': is_alive, 'last_login': last_login}
                result.append(stat)
    return result

def search_prefab(search_word):
    update_prefabs()
    reverse_prefabs = get_reverse_prefabs()
    if search_word in reverse_prefabs:
        prefabs = reverse_prefabs[search_word]
        if len(prefabs) > 1:
            return {}
        else:
            search_word = prefabs[0]
    if search_word in PREFABS or all(map(lambda x: ord(x)<128, search_word)):
        prefab = search_word
        result = countprefab(prefab, CLUSTER_DIR)
        r = {ku_to_name(session_to_ku(k)): v 
                for k, v in result['user'].items()}
        result['user'] = r
    else:
        return {}
    return result

def upload_archive():
    result = zip_cluster(CLUSTER_DIR)
    return result

def edit_cluster(option):
    if option:
        res = _edit_cluster(option)
    else:
        res = print_config()
    return res


def main():
    R = redis.Redis(decode_responses=True)
    print("Daemon Start")
    while True:
        print("Listening for task...")
        task_json = R.blpop(REDIS_TASK_KEY)
        task_name, *params, task_code = json.loads(task_json[1])
        print(f"Accept task {task_name}")
        if task_name in TASK_DICT:
            task_fn = TASK_DICT[task_name]
            result = task_fn(*params)
            result_key = REDIS_TASK_RESULT_KEY_PREPEND+task_code
            result_json = json.dumps(result)
            R.set(result_key, result_json, ex=60)
            print("task complete")
        else:
            print(f'task name: {task_name} NOT FOUND')


TASK_DICT = {
    'search_prefab': search_prefab,
    'upload_archive': upload_archive,
    'backup': backup,
    'edit_cluster': edit_cluster,
    'get_users_stat': get_users_stat,
    'ban': ban_player,
    'kick': kick_player,
    'drop': drop_player_everything,
}

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Daemon Exit")