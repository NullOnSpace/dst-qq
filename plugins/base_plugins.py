from nonebot import on_command, on_request, on_notice, \
        NoticeSession, RequestSession, CommandSession, permission as perm
from nonebot.command import kill_current_session
from redis import asyncio as aioredis
from aiocqhttp.exceptions import ActionFailed

import asyncio
import json
from hashlib import sha1
import time
import datetime
import os
import shutil
import string

from utils.dst.get_server_list_aio import get_server, get_server_detail
from utils.dst.get_versions import aio_get_latest_version
from . import customize_strings as cs
from config import ADMINS
from .custmize_permission import check_permission


HOST = "KU_3RvV9haR"
STRING_MODEL = """服务器名: \n\t{server_name}
玩家: {connected}/{max_connections}
季节: {season}{season_elapsed}
天数: {day}
版本: {version}
"""
KU_STR = string.ascii_letters + string.digits + "_-"

REDIS_QBOT_COMMAND = "dst:qbot:command"
REDIS_SERVER_STATE = "dst:server:state"
REDIS_UPDATE_STATE = "dst:update:server"
REDIS_TASK_KEY = 'DST:DAEMON:TASKS'
REDIS_TASK_RESULT_KEY_PREPEND = 'DST:DAEMON:TASK_DONE:'
REDIS_SERVER_INFO = "dst:server:info"
REDIS_CONSOLE_COMAND = "dst:server:console:command"
REDIS_CHAT = "dst:chat:sorted-set"
REDIS_CHAT_LAST_FETCH = "dst:chat:last-fetch"
REDIS_KU_MAPPING = "dst:user:ku"
REDIS_KU_LA = "dst:user:lastaccess"
REDIS_KU_QQ_MAPPING = "dst:qgroup:ku"

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


# helper functions

async def split_send_msg(session: CommandSession, msg: str):
    print(f"msg len: {len(msg)}")
    ret = await session.send(msg)
    print(f"send msg result: {ret}")
    if ret is None:
        # send msg failed
        # split and send
        lines = msg.split("\n")
        throat = 100
        msg_slice_list = []
        for line in lines:
            msg_slice_list.append(line)
            msg_slice = "\n".join(msg_slice_list)
            if len(msg_slice) > throat:
                msg_slice = "\n".join(msg_slice_list[:-1])
                await session.send(msg_slice)
                msg_slice_list = [line,]
        else:
            if msg_slice_list:
                msg_slice = "\n".join(msg_slice_list)
                await session.send(msg_slice)

def puralize_ku(ku_origin: str):
    if len(ku_origin) == 11 and ku_origin.startswith("KU_"):
        if all(map(lambda x: x in KU_STR, ku_origin)):
            return ku_origin
    elif len(ku_origin) == 10 and ku_origin.startswith("KU"):
        if all(map(lambda x: x in KU_STR, ku_origin)):
            ku = ku_origin[:2] + "_" + ku_origin[2:]
            return ku
    elif len(ku_origin) == 8:
        if all(map(lambda x: x in KU_STR, ku_origin)):
            ku = "KU_" + ku_origin
            return ku
    return None


# commands without any perm

@on_command('quest', aliases=('查全服',), only_to_me=True)
async def quest(session: CommandSession):
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
    r = '-----------\n'.join(reports) or "没有找到服务器涅"
    await session.send(r)

@on_command('info', aliases=('查服',), only_to_me=True)
async def info(session: CommandSession):
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    i = await r.get(REDIS_SERVER_INFO)
    if i:
        await session.send(i)
    else:
        await session.send("查询不到服务器")

@on_command('version', aliases=('版本',), only_to_me=True)
async def get_version(session: CommandSession):
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
async def search_prefab(session: CommandSession):
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
    await split_send_msg(session, msg)

@on_command('chat', aliases=('聊天',), only_to_me=True)
async def chat(session: CommandSession):
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    msg = session.current_arg_text.strip()
    ctx = session.ctx
    message_type = ctx['message_type']
    sender = ctx['sender']
    msg_len_limit = 50
    print(dict(ctx.items()))
    if msg:
        # send msg to server
        if len(msg) > msg_len_limit:
            await session.send(f"消息过长 请在{msg_len_limit}字以内")
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
            await split_send_msg(session, "\n".join(msgs))
        else:
            await session.send("没有更多的新消息了")

@on_command('player', aliases=('玩家',), only_to_me=True)
async def player_statistics(session: CommandSession):
    print("player statistics")
    ORDER_BY = {
        '时长': 'age',
        '时间': 'last_login'
    }
    HELP = "输入 '/玩家 排序依据' 来查看玩家统计 排序依据有 '时长' '时间' 默认时长"
    PLAYER_FMT = "{ku} [{last_login}]\n[{username}] {age:>4}天"
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    order_by = session.current_arg_text.strip()
    if (not order_by) or \
            order_by in ORDER_BY.keys() or order_by in ORDER_BY.values():
        await session.send("正在处理...")
        task_code = sha1(str(time.time()).encode()).hexdigest()
        if order_by in ORDER_BY:
            order_by = ORDER_BY[order_by]
        elif not order_by:
            order_by = 'age'
        task = ('get_users_stat', task_code)
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
                players = sorted(result, 
                        key=lambda x: x[order_by], reverse=True)[:15]
                for player in players:
                    dt = datetime.datetime.fromtimestamp(player['last_login'])
                    last_login = dt.strftime("%m-%d %H:%M")
                    msg += PLAYER_FMT.format(
                        ku=player['ku'], username=player['username'],
                        age=int(player['age']//480+1), last_login=last_login,
                    )
                    if not player['is_alive']:
                        msg += "\u2620"
                    msg += "\n"
                msg = msg or "没有信息"
                break
    else:
        msg = HELP
    await split_send_msg(session, msg)

@on_command('admin', aliases=('管理员',), only_to_me=True)
async def get_admin(session: CommandSession):
    HELP = "在群内输入 '/管理员' 查看该群内管理员"
    ctx = session.ctx
    msg_type = ctx['message_type']
    FMT = " {user_id}: [{username}]\n"
    # user_id =  ctx['user_id']
    if msg_type == "group":
        group_id = ctx['group_id']
        rt = await session.bot.call_action('get_group_member_list', 
                        group_id=group_id,
                    )
        print(f"testing: {rt}")
        group_dict = {i['user_id']: i for i in rt}
        msg = ""
        for user_id in sorted(ADMINS):
            if user_id in group_dict:
                info = group_dict[user_id]
                user_name = info['card'] or info['nickname']
                msg += FMT.format(
                    user_id=user_id, username=user_name)
        if msg:
            msg = "管理员:\n" + msg
        else:
            msg = "没有管理员"
    else:
        msg = HELP
    await split_send_msg(session, msg)

@on_command('kill', aliases=('闭嘴'), only_to_me=True, privileged=True)
async def kill(session: CommandSession):
    kill_current_session(session.event)

# commands with admin perms

@on_command('start', aliases=('启动',), only_to_me=True)
@check_permission('admin')
async def start(session: CommandSession):
    print("start")
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    await r.delete(REDIS_SERVER_STATE)
    await r.lpush(REDIS_QBOT_COMMAND, 'start')
    last_state = ""
    starting_strings = []
    t_start = time.time()
    timeout = 100
    while True:
        _, state = await r.brpop(REDIS_SERVER_STATE)
        if last_state != state:
            t_start = time.time()
            print(f"last: {last_state}, current: {state}")
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
        if time.time() - t_start > timeout:
            await session.send("启动超时")
            return

@on_command('stop', aliases=('关机',), only_to_me=True)
@check_permission('admin')
async def stop(session: CommandSession):
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

@on_command('update', aliases=('更新',), only_to_me=True)
@check_permission('admin')
async def update(session: CommandSession):
    print("update")
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    await r.delete(REDIS_UPDATE_STATE)
    await r.lpush(REDIS_QBOT_COMMAND, 'update')
    await session.send("updating")
    last_state = ""
    while True:
        state = await r.get(REDIS_UPDATE_STATE)
        if state: 
            if "6" in state:
                if last_state != state:
                    print(last_state, state)
                    last_state = state
                    await session.send(state)
            else:
                await session.send(state)
                await r.close()
                break
        await asyncio.sleep(0.2)
    await r.close()

@on_command('rollback', aliases=('回档',), only_to_me=True)
@check_permission('admin')
async def rollback(session: CommandSession):
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
        await r.delete(REDIS_SERVER_STATE)
        await r.lpush(REDIS_CONSOLE_COMAND, f"c_rollback({days})")
        await session.send(f"正尝试回档 {days}")
        rb = False
        while True:
            state_tp = await r.brpop(REDIS_SERVER_STATE, timeout=45)
            if state_tp is None:
                await session.send("回档超时")
                r.close()
                return
            else:
                state = state_tp[1]
                print(f"get state: {state} in rollback polling")
            if rb is False:
                if state == "rollback":
                    rb = True
                    await session.send("开始回档")
            else:
                if state == "running":
                    await session.send("回档完成")
                    r.close()
                    return
    else:
        await session.send(HELP_MESSAGE)
        r.close()
    return 

@on_command('upload', aliases=('归档',), only_to_me=True)
@check_permission('admin')
async def upload(session: CommandSession):
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

@on_command('drop', aliases=('掉落',), only_to_me=True)
@check_permission('admin')
async def drop_player(session: CommandSession):
    print("drop player")
    HELP_MESSAGE = "输入 '/掉落 玩家KU' 来使玩家物品掉落"
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    ku_raw = session.current_arg_text.strip()
    if ku_raw:
        ku = puralize_ku(ku_raw)
        if ku is None:
            await session.send(f"无效的KU: {ku_raw}")
            return
        task_code = sha1(str(time.time()).encode()).hexdigest()
        task = ('drop', ku, task_code)
        task_json = json.dumps(task)
        await r.rpush(REDIS_TASK_KEY, task_json)
        msg = f"掉落[{ku}]的物品"
    else:
        msg = HELP_MESSAGE
    await session.send(msg)

@on_command('kick', aliases=('踢',), only_to_me=True)
@check_permission('admin')
async def kick_player(session: CommandSession):
    print("kick player")
    HELP_MESSAGE = "输入 '/踢 玩家KU 秒数' 来将玩家踢出房间一段时间 默认10分钟"
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    text = session.current_arg_text.strip()
    if text:
        seconds = 10*60
        if " " in text:
            parts = text.split(" ")
            ku_raw = parts[0]
            seconds_str = parts[-1]
            if seconds_str.isdigit():
                seconds = int(seconds_str)
        else:
            ku_raw = text
        ku = puralize_ku(ku_raw)
        if ku is None:
            await session.send(f"无效的KU: {ku_raw}")
            return
        task_code = sha1(str(time.time()).encode()).hexdigest()
        task = ('kick', ku, seconds, task_code)
        task_json = json.dumps(task)
        await r.rpush(REDIS_TASK_KEY, task_json)
        msg = f"将[{ku}]踢出房间 {seconds}秒"
    else:
        msg = HELP_MESSAGE
    await session.send(msg)

@on_command('ban', aliases=('禁',), only_to_me=True)
@check_permission('admin')
async def ban_player(session: CommandSession):
    print("ban player")
    HELP_MESSAGE = "输入 '/禁 玩家KU' 来禁止玩家在房间游戏"
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    ku_raw = session.current_arg_text.strip()
    if ku_raw:
        ku = puralize_ku(ku_raw)
        if ku is None:
            await session.send(f"无效的KU: {ku_raw}")
            return
        task_code = sha1(str(time.time()).encode()).hexdigest()
        task = ('ban', ku, task_code)
        task_json = json.dumps(task)
        await r.rpush(REDIS_TASK_KEY, task_json)
        msg = f"禁止[{ku}]在本房间游戏"
    else:
        msg = HELP_MESSAGE
    await session.send(msg)


# commands with superuser perms

@on_command('regen', aliases=('重置',), only_to_me=True, 
        permission=perm.SUPERUSER)
async def regen(session: CommandSession):
    print("regenerate world")
    HELP_MESSAGE = "输入 '/重置' 来重置世界"
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    await r.delete(REDIS_SERVER_STATE)
    await r.lpush(REDIS_CONSOLE_COMAND, f"c_regenerateworld()")
    await session.send(f"正尝试重置世界")
    rg = False
    while True:
        state_tp = await r.brpop(REDIS_SERVER_STATE, timeout=50)
        if state_tp is None:
            await session.send("重置超时")
            return
        else:
            state = state_tp[1]
            print(f"get state:{state} in regenerate polling")
        if rg is False:
            if state == "regenerate":
                rg = True
                await session.send(f"开始重置")
        else:
            if state == "running":
                await session.send("重置完成")
                break

@on_command('edit_cluster', aliases=('服务器设置',),
        permission=perm.SUPERUSER, only_to_me=True)
async def edit_cluster(session: CommandSession):
    print("edit cluster ini")
    HELP_MESSAGE = "输入 '/服务器设置 设置名 设置值' 来修改服务器设置"
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    option = session.current_arg_text.strip()
    if option:
        await session.send("正在处理...")
        task_code = sha1(str(time.time()).encode()).hexdigest()
        opt, val = option.split(" ", maxsplit=1)
        task = ('edit_cluster', {opt: val}, task_code)
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
                errors = json.loads(result_json)
                if errors:
                    msg = " ".join(errors) + "不是可修改选项"
                else:
                    msg = "成功修改"
                break
    else:
        msg = HELP_MESSAGE
    await session.send(msg)


@on_command('test', aliases=('测试',), only_to_me=True)
@check_permission('admin')
async def _test(session: CommandSession):
    msg = "empty"
    ctx = session.ctx
    msg_type = ctx['message_type']
    FMT = " {user_id}: [{username}]\n"
    # user_id =  ctx['user_id']
    if msg_type == "group":
        group_id = ctx['group_id']
        rt = await session.bot.call_action('get_group_member_list', 
                        group_id=655462253,
                    )
        print(f"testing: {rt}")
        group_dict = {i['user_id']: i for i in rt}
        msg = ""
        for user_id in sorted(ADMINS):
            if user_id in group_dict:
                info = group_dict[user_id]
                user_name = info['card'] or info['nickname']
                msg += FMT.format(
                    user_id=user_id, username=user_name)
        if msg:
            msg = "管理员:\n" + msg
        else:
            msg = "没有管理员"
    await session.send(msg)


@on_request('group')
async def group_add(session: RequestSession):
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    comment = session.event.comment
    cmt = comment.split("\n答案：")[-1]
    if cmt and cmt.strip():
        ku = await check_nickname(cmt)
        if ku:
            await r.hset(REDIS_KU_QQ_MAPPING, 
                str(session.ctx['user_id']), ku)
            session.approve()
    return


async def check_nickname(nickname):
    # check if nickname in redis ku list in 2 days
    # return True or False
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    ku_las = await r.hgetall(REDIS_KU_LA)
    now_ts = time.time()
    time_diff = 2*24*3600
    ku_in_2days = set(k for k, la in ku_las if now_ts - int(la) <= time_diff)
    if len(nickname) <= 3:
        for ku in ku_in_2days:
            name = await r.hget(REDIS_KU_MAPPING, ku)
            if name == nickname:
                return ku
    else:
        for ku in ku_in_2days:
            name = await r.hget(REDIS_KU_MAPPING, ku)
            common = set(name.lower()) & set(nickname.lower())
            if name.startswith(nickname) or len(common) > 0.8*len(nickname):
                return ku
    return False

@on_notice('group_increase')
async def group_increase(session: NoticeSession):
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    user_id = session.ctx['user_id']
    ku = await r.hget(REDIS_KU_QQ_MAPPING, str(user_id))
    if ku:
        nickname = await r.hget(REDIS_KU_MAPPING, ku)
        if nickname:
            await session.send(f"欢迎{nickname}")