import redis

from hashlib import sha1
import time
import json
import os
import shutil


REDIS_QBOT_COMMAND = "dst:qbot:command"
REDIS_SERVER_STATE = "dst:server:state"
REDIS_UPDATE_STATE = "dst:update:server"
REDIS_TASK_KEY = 'DST:DAEMON:TASKS'
REDIS_TASK_RESULT_KEY_PREPEND = 'DST:DAEMON:TASK_DONE:'
REDIS_SERVER_INFO = "dst:server:info"
REDIS_CONSOLE_COMAND = "dst:server:console:command"
REDIS_CHAT = "dst:chat:sorted-set"
REDIS_CHAT_LAST_FETCH = "dst:chat:last-fetch"


STATE_DICT = {
    "idle": "空闲",
    "starting": "正在启动",
    "shutting down": "正在关闭",
    "running": "运行中",
    "ERROR": "服务器错误",
    "setup timeout": "启动超时",
    "start stuck": "启动受阻",
    "rollback": "回档",
}

def regenerate():
    print("regenerate world")
    r = redis.from_url("redis://localhost", decode_responses=True)
    r.lpush(REDIS_CONSOLE_COMAND, f"c_regenerateworld()")
    rg = False
    while True:
        state_tp = r.brpop(REDIS_SERVER_STATE, timeout=70)
        if state_tp is None:
            print("重置超时")
            return False
        else:
            state = state_tp[1]
            print(f"get state:{state} in regenerate polling")
        if rg is False:
            if state == "regenerate":
                print("开始重置")
                rg = True
        else:
            if state == "running":
                print("重置完成")
                return True

def zip_cluster():
    print("upload archive")
    r = redis.from_url("redis://localhost", decode_responses=True)
    task_code = sha1(str(time.time()).encode()).hexdigest()
    task = ('upload_archive', task_code)
    task_json = json.dumps(task)
    r.rpush(REDIS_TASK_KEY, task_json)
    result_key = REDIS_TASK_RESULT_KEY_PREPEND + task_code
    max_tries = 120
    while True:
        result_json = r.get(result_key)
        if result_json is None:
            time.sleep(2)
            max_tries -= 1
            if max_tries <= 0:
                print("请求超时")
                return False
        else:
            r.delete(result_key)
            result = json.loads(result_json)
            print(f"receive result {result}")
            maps = result['maps']
            file_7z = result['7z']
            temp_dir = result['temp_dir']
            # map always in MyDediServer so no need to copy or move it
            shutil.rmtree(temp_dir)
            return True

def start_up():
    print("start")
    r = redis.from_url("redis://localhost", decode_responses=True)
    r.delete(REDIS_SERVER_STATE)
    r.lpush(REDIS_QBOT_COMMAND, 'start')
    last_state = ""
    while True:
        _, state = r.brpop(REDIS_SERVER_STATE)
        if last_state != state:
            print(last_state, state)
            last_state = state
            if "/" in state:
                print(f"启动状态{state}")
            elif state in ('idle', 'starting'):
                print(STATE_DICT[state])
            else:
                print(STATE_DICT[state])
                r.close()
                return True

def shutdown():
    print("stop")
    r = redis.from_url("redis://localhost", decode_responses=True)
    r.lpush(REDIS_QBOT_COMMAND, 'stop')
    print("正在关机")
    t_start = time.time()
    timeout = 30
    while True:
        if time.time() - t_start > timeout:
            print("关机超时")
            return False
        _, server_status = r.brpop(REDIS_SERVER_STATE)
        if server_status == "idle":
            print("已关闭")
            return True


def roll_maps():
    start_up()
    try:
        while True:
            zip_cluster()
            print("have a rest")
            time.sleep(5)
            print("rest over")
            regenerate()
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    start_up()
    try:
        print("started waiting")
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        shutdown()