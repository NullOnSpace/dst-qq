import json
import os 
import sys

CWD = os.path.dirname(__file__)
sys.path.append(CWD)
from manage_server.get_config import CLUSTER_DIR
from manage_server.parse_save import countprefab
from manage_server.get_prefab_list import PREFABS, REVERSE_PREFABS
from manage_server.manage_user import session_to_ku, ku_to_name
from manage_server.archive_cluster import zip_cluster
from manage_server.mega_backup import backup
from manage_server.edit_setting import edit as _edit_cluster, print_config

import redis

REDIS_TASK_KEY = 'DST:DAEMON:TASKS'
REDIS_TASK_RESULT_KEY_PREPEND = 'DST:DAEMON:TASK_DONE:'

def search_prefab(search_word):
    if search_word in REVERSE_PREFABS:
        prefabs = REVERSE_PREFABS[search_word]
        if len(prefabs) > 1:
            return {}
        else:
            search_word = prefabs[0]
    if search_word in PREFABS:
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
}

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Daemon Exit")