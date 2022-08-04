from nonebot import on_command, CommandSession, permission as perm
import aioredis

import asyncio

from utils.dst.get_server_list_aio import get_server, get_server_detail


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

# @on_command('version', aliases=('版本',), only_to_me=TEST)
# async def version(session):
#     await session.send(message)

REDIS_CHANNEL = "dst:channel:server"
REDIS_SERVER_STATE = "dst:state:server"
REDIS_UPDATE_STATE = "dst:update:server"

@on_command('start', aliases=('启动',),
    permission=perm.SUPERUSER, only_to_me=TEST)
async def start(session):
    print("start")
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    await r.publish(REDIS_CHANNEL, 'start')
    last_state = ""
    while True:
        state = await r.get(REDIS_SERVER_STATE)
        if state in ('1/4', '2/4', '3/4', 'idle', 'starting'):
            if last_state != state:
                print(last_state, state)
                last_state = state
                await session.send(state)
        else:
            await session.send(state)
            await r.close()
            return
        await asyncio.sleep(0.2)

@on_command('stop', aliases=('关机',),
    permission=perm.SUPERUSER, only_to_me=TEST)
async def stop(session):
    print("stop")
    r = aioredis.from_url("redis://localhost", decode_responses=True)
    await r.publish(REDIS_CHANNEL, 'stop')
    await session.send("closed")
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
