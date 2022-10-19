from nonebot import on_command, CommandSession, permission as perm
import aioredis

import asyncio
import json
from hashlib import sha1
import time

from utils.dst.get_server_list_aio import get_server, get_server_detail
from utils.dst.get_versions import aio_get_latest_version
from utils.dst.server_daemon import REDIS_TASK_KEY
from . import customize_strings as cs


HOST = "KU_3RvV9haR"
STRING_MODEL = """服务器名: \n\t{server_name}
玩家: {connected}/{max_connections}
季节: {season}{season_elapsed}
天数: {day}
版本: {version}
"""
TEST = False

@on_command('quest', aliases=('查服',), only_to_me=TEST)
async def quest(session):
    print(1)
    servers = await get_server()
    print(2)
    server_list = servers['List']
    report = ""
    if server_list:
        for server in server_list:
            if server['Host'] == HOST:
                server_name = server['Name']
                connected = server['Connected']
                max_connections = server['MaxConnections']
                season = server['Season']
                row_id = server['RowId']
                r = await get_server_detail(row_id)
                print(3)
                days_info = r['DaysInfo']
                day = days_info['Day']
                season_elapsed = int(days_info['DaysElapsedInSeason']) + 1
                version = r['Version']
                players = r['Players']
                report = STRING_MODEL.format(**locals())
                if players:
                    report += "玩家列表:\n"
                for player in players:
                    report += f"\t{player['Name']} ({player['Prefab']})\n"
    else:
        report = "没有找到服务器涅"
    await session.send(report)


REDIS_CHANNEL = "dst:channel:server"
REDIS_SERVER_STATE = "dst:state:server"
REDIS_UPDATE_STATE = "dst:update:server"
REDIS_TASK_KEY = 'DST:DAEMON:TASKS'
REDIS_TASK_RESULT_KEY_PREPEND = 'DST:DAEMON:TASK_DONE:'

STATE_DICT = {
    "idle": "空闲",
    "starting": "正在启动",
    "stopping": "正在关闭",
    "running": "运行中",
    "ERROR": "服务器错误",
    "setup timeout": "启动超时",
}

@on_command('start', aliases=('启动',),
    permission=perm.SUPERUSER, only_to_me=TEST)
async def start(session):
    print("start")
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    await r.publish(REDIS_CHANNEL, 'start')
    last_state = ""
    starting_strings = []
    while True:
        state = await r.get(REDIS_SERVER_STATE)
        if last_state != state:
            print(last_state, state)
            last_state = state
            if "/" in state:
                order, total = state.split("/")
                if not starting_strings:
                    starting_strings = cs.give_some_startings(int(total))
                s = starting_strings[int(order)-1]
                await session.send(f"{s}...{state}")
            elif state in ('idle', 'starting'):
                await session.send(STATE_DICT[state])
            else:
                await session.send(STATE_DICT[state])
                await r.close()
                return
        await asyncio.sleep(0.2)

@on_command('stop', aliases=('关机',),
    permission=perm.SUPERUSER, only_to_me=TEST)
async def stop(session):
    print("stop")
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    await r.publish(REDIS_CHANNEL, 'stop')
    await session.send("正在关机")
    while True:
        server_status = await r.get(REDIS_SERVER_STATE)
        if server_status != "stopping":
            break
    await session.send("已关闭")
    await r.close()

@on_command('update', aliases=('更新',),
    permission=perm.SUPERUSER, only_to_me=TEST)
async def update(session):
    print("update")
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    await r.publish(REDIS_CHANNEL, 'update')
    await session.send("updating")
    await r.set(REDIS_UPDATE_STATE, "start")
    last_state = ""
    while True:
        state = await r.get(REDIS_UPDATE_STATE)
        if state == "start":
            continue
        if "6" in state:
            if last_state != state:
                print(last_state, state)
                last_state = state
                await session.send(state)
        else:
            await session.send(state)
            await r.close()
            return
        await asyncio.sleep(0.2)
    await r.close()


@on_command('version', aliases=('版本',), only_to_me=TEST)
async def get_version(session):
    print("get version")
    HELP_MESSAGE = "输入 '/版本 正式' 或 '/版本 测试'"
    meta_info = session.current_arg_text.strip()
    if meta_info.lower() in ("", "正式", "realease"):
        msg = await aio_get_latest_version(False)
    elif meta_info.lower() in ("测试", "test"):
        msg = await aio_get_latest_version(True)
    else:
        msg = HELP_MESSAGE
    await session.send(msg)


@on_command('search', aliases=('查找',), only_to_me=TEST)
async def search_prefab(session):
    print("search prefab")
    HELP_MESSAGE = "输入 '/查找 物品名' 来查看物品数量"
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    prefab = session.current_arg_text.strip()
    if prefab:
        await session.send("正在处理...")
        task_code = sha1(str(time.time()).encode()).hexdigest()
        task = ('search_prefab', prefab, task_code)
        task_json = json.dumps(task)
        await r.rpush(REDIS_TASK_KEY, task_json)
        result_key = REDIS_TASK_RESULT_KEY_PREPEND + task_code
        max_tries = 10
        while True:
            result_json = await r.get(result_key)
            if result_json is None:
                await asyncio.sleep(2)
                max_tries -= 1
                if max_tries <= 0:
                    msg = "请求超时"
                    break
            else:
                await r.delete(result_key)
                result = json.loads(result_json)
                msg = ""
                map_count = result.get('map', 0)
                if map_count:
                    msg += f"世界中有{map_count}处{prefab}\n"
                user_count = result.get('user')
                if user_count:
                    if map_count:
                        msg += "另外,\n"
                    for username, ct in user_count.items():
                        msg += f"玩家: {username} 身上有{ct}个{prefab}\n"
                if not map_count and not user_count:
                    msg = f"世界中没找到名为 {prefab} 的物品"
                break
    else:
        msg = HELP_MESSAGE
    await session.send(msg)