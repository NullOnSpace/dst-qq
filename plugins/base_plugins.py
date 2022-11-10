from nonebot import on_command, CommandSession, permission as perm
from redis import asyncio as aioredis
from aiocqhttp.exceptions import ActionFailed

import asyncio
import json
from hashlib import sha1
import time
import os
import shutil

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

@on_command('quest', aliases=('旧查服',), only_to_me=True)
async def quest(session):
    servers = await get_server()
    server_list = servers['List']
    reports = []
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
                reports.append(report)
    r = '-------\n'.join(reports) or "没有找到服务器涅"
    await session.send(r)

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

@on_command('info', aliases=('服务器状态', '查服'), only_to_me=True)
async def info(session):
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    i = await r.get(REDIS_SERVER_INFO)
    if i:
        await session.send(i)
    else:
        await session.send("查询不到服务器")

@on_command('start', aliases=('启动',),
    permission=perm.SUPERUSER, only_to_me=True)
async def start(session):
    print("start")
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    await r.delete(REDIS_SERVER_STATE)
    await r.lpush(REDIS_QBOT_COMMAND, 'start')
    last_state = ""
    starting_strings = []
    while True:
        _, state = await r.brpop(REDIS_SERVER_STATE)
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

@on_command('stop', aliases=('关机',),
    permission=perm.SUPERUSER, only_to_me=True)
async def stop(session):
    print("stop")
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    await r.lpush(REDIS_QBOT_COMMAND, 'stop')
    await session.send("正在关机")
    t_start = time.time()
    timeout = 30
    while True:
        if time.time() - t_start > timeout:
            await session.send("关机超时")
            break
        _, server_status = await r.brpop(REDIS_SERVER_STATE)
        if server_status == "idle":
            await session.send("已关闭")
            break
    await r.close()

@on_command('update', aliases=('更新',),
    permission=perm.SUPERUSER, only_to_me=True)
async def update(session):
    print("update")
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    await r.delete(REDIS_UPDATE_STATE)
    await r.lpush(REDIS_QBOT_COMMAND, 'update')
    await session.send("updating")
    last_state = ""
    while True:
        state = await r.get(REDIS_UPDATE_STATE)
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


@on_command('version', aliases=('版本',), only_to_me=True)
async def get_version(session):
    print("get version")
    HELP_MESSAGE = "输入 '/版本 正式' 或 '/版本 测试'"
    meta_info = session.current_arg_text.strip()
    if meta_info.lower() in ("", "正式", "release"):
        msg = await aio_get_latest_version(False)
    elif meta_info.lower() in ("测试", "test"):
        msg = await aio_get_latest_version(True)
    else:
        msg = HELP_MESSAGE
    await session.send(msg)


@on_command('search', aliases=('查找',), only_to_me=True)
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

@on_command('rollback', aliases=('回档',), only_to_me=True, 
        permission=perm.SUPERUSER)
async def rollback(session):
    print("rollback")
    HELP_MESSAGE = "输入 '/回档 天数'如 '/回档 2' 来回档 一次最多3天"
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    days_str = session.current_arg_text.strip()
    if days_str.isdigit():
        days = int(days_str)
    elif days_str == "":
        days = 0
    else:
        days = -99999
    if days >= 0 and days <= 3:
        await r.lpush(REDIS_CONSOLE_COMAND, f"c_rollback({days})")
        await session.send(f"正尝试回档 {days}")
        rb = False
        while True:
            state_tp = await r.brpop(REDIS_SERVER_STATE, timeout=30)
            if state_tp is None:
                await session.send("回档超时")
                return
            else:
                state = state_tp[1]
                print(f"get state:{state} in rollback polling")
            if rb is False:
                if state == "rollback":
                    rb = True
                    await session.send(f"开始回档")
            else:
                if state == "running":
                    await session.send("回档完成")
                    break
    else:
        await session.send(HELP_MESSAGE)

@on_command('chat', aliases=('聊天',), only_to_me=True)
async def chat(session):
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    msg = session.current_arg_text.strip()
    ctx = session.ctx
    message_type = ctx['message_type']
    sender = ctx['sender']
    print(dict(ctx.items()))
    if msg:
        # send msg to server
        if len(msg) > 30:
            return
        if message_type == 'group':
            nickname = sender.get("card") or sender.get("nickname")
            msg = f"群聊[{nickname}]: {msg}"
        msg = msg.replace('"', "'")
        await r.lpush(REDIS_CONSOLE_COMAND, f'c_announce("{msg}")')
        await session.send(f"已发送")
    else:
        # fetch msg from server
        id_ = ctx['group_id'] if message_type == 'group' else ctx['user_id']
        field = message_type + ":" + str(id_)
        last_fetch_ts = await r.hget(REDIS_CHAT_LAST_FETCH, field)
        if last_fetch_ts is None:
            last_fetch_ts = 0
        else:
            last_fetch_ts = float(last_fetch_ts)
        msgs = await r.zrevrangebyscore(
                REDIS_CHAT, 
                min=last_fetch_ts, max=9e11,
                start=0, num=10
        )
        await r.hset(REDIS_CHAT_LAST_FETCH, field, time.time())
        if msgs:
            await session.send("\n".join(msgs))
        else:
            await session.send("没有更多的新消息了")


@on_command('upload', aliases=('归档',), 
        permission=perm.SUPERUSER, only_to_me=True)
async def upload(session):
    print("upload archive")
    HELP_MESSAGE = "在群内输入 '/归档' 上传归档和地图到群文件"
    ctx = session.ctx
    msg_type = ctx['message_type']
    if msg_type != "group":
        msg = HELP_MESSAGE
    else:
        group_id = ctx['group_id']
        r = aioredis.from_url("redis://localhost", decode_responses=True)
        await session.send("正在处理...")
        task_code = sha1(str(time.time()).encode()).hexdigest()
        task = ('upload_archive', task_code)
        task_json = json.dumps(task)
        await r.rpush(REDIS_TASK_KEY, task_json)
        result_key = REDIS_TASK_RESULT_KEY_PREPEND + task_code
        max_tries = 120
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
                print(f"receive result {result}")
                maps = result['maps']
                file_7z = result['7z']
                temp_dir = result['temp_dir']
                try:
                    await session.bot.call_action('upload_group_file', 
                        group_id=group_id, file=file_7z, 
                        name=file_7z.split("/")[-1],
                    )
                    for map in maps:
                        await session.bot.call_action('upload_group_file', 
                            group_id=group_id, file=map, 
                            name=map.split("/")[-1],
                        )
                except ActionFailed:
                    msg = "上传失败"
                else:
                    msg = "上传成功"
                os.remove(file_7z)
                shutil.rmtree(temp_dir)
                break
    await session.send(msg)
    
