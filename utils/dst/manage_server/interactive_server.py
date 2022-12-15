import configparser
import os
import os.path
import subprocess
from signal import SIGINT
import time
import threading
import re
import datetime
import logging
import logging.handlers
import json
import sys
import multiprocessing as mp

import redis

CWD = os.path.dirname(__file__)
sys.path.append(CWD)
from get_prefab_list import PREFABS
from remote_command_patterns import PTNS, FIND_A_PLAYER_PATTERN as FPTN
from get_config import STEAMCMD_DIR, INSTALL_DIR, DONTSTARVE_DIR, CLUSTER_NAME
from edit_mod import add_server_mod_to_auto_update


COMMAND = "dontstarve_dedicated_server_nullrenderer_x64"

REDIS_SERVER_STATE = "dst:server:state"
REDIS_SERVER_COMMAND = "dst:server:command"
REDIS_SERVER_INFO = "dst:server:info"
REDIS_CONSOLE_COMAND = "dst:server:console:command"
REDIS_KU_MAPPING = "dst:user:ku"
REDIS_KU_LA = "dst:user:lastaccess"
REDIS_CHAT = "dst:chat:sorted-set"
REDIS_UPDATE_STATE = "dst:update:server"
REDIS_QBOT_COMMAND = "dst:qbot:command"
REDIS_TASK_KEY = 'DST:DAEMON:TASKS'
REDIS_PREFABS = 'dst:data:prefabs'

AUTH_PATTERN = re.compile("Client authenticated: \((?P<ku>[\w\d\-_]+)\) (?P<name>.+)$")
IP_PATTERN = re.compile("New incoming connection (?P<ip>[\d+.]+)\|\d+ <(?P<uid>\d+)>$")
START_TIME_PATTERN = re.compile("Current time: (?P<datetime>.+)")
TIME_PATTERN = re.compile("^\[(?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+)\]")
CHAT_PATTERN = re.compile("\[(Say|Whisper)\] \((?P<ku>[A-Za-z0-9_-]+)\) (?P<name>[^:]+): (?P<message>.*)$")
ROLLBACK_PATTERN = re.compile("Received world rollback request: count=(?P<count>\d+)")
REMOTE_COMMAND_PATTERN = re.compile("\[\((?P<ku>[\w\d\-_]+)\) (?P<name>[^\]]+)\] ReceiveRemoteExecute\((?P<content>.+)\) @\((?P<cord>.+)\)")

MESSAGE_FORMAT = "[{datetime}] ({username}): {msg}"
_GET_SRVER_INFO_COMMAND = """
local json = string.format('"server_name": "%s", "max_players": "%s", "game_mode": "%s", ', TheNet:GetDefaultServerName(), TheNet:GetDefaultMaxPlayers(), TheNet:GetDefaultGameMode());
local status = string.format('"daysinseason": %s, "season": "%s", "days": %s, ', TheWorld.state.elapseddaysinseason, TheWorld.state.season, TheWorld.state.cycles);
json = json..status;
local players = {};
local gamers = "";
for n, v in ipairs(TheNet:GetClientTable()) do 
    players[n] = {};
    players[n]["name"] = v.name;
    players[n]["prefab"] = v.prefab; 
    players[n]["age"] = v.playerage; 
    if v.steamid == nil or v.steamid == '' then 
        players[n]["steamid"] = v.netid;
    else 
        players[n]["steamid"] = v.steamid;
    end
    players[n]["userid"] = v.userid; 
    players[n]["admin"] = v.admin;
    local gamer = string.format('{"name": "%s", "prefab": "%s", "playerage": %s, "steamid": "%s", "userid": "%s", "admin": %s}', v.name, v.prefab, v.playerage, tostring(v.steamid or v.netid), v.userid, tostring(v.admin));
    if n == 1 then
        gamers = gamers..gamer;
    else
        gamers = gamers..','..gamer;
    end;
end;
json = json..'"player_list":['..gamers..']';
json = '{'..json..'}';
print(string.format("[server status] %s", json));
"""
GET_SERVER_INFO_COMMAND = " ".join(_GET_SRVER_INFO_COMMAND.split("\n"))
GET_PREFABS_COMMAND = """for k, v in pairs(STRINGS.NAMES) do print(string.format("[prefab] %s:%s", k, v)) end"""

TZ = datetime.timezone(datetime.timedelta(hours=8), name="Asia/Shanghai")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.addHandler(logging.handlers.RotatingFileHandler(
    filename=os.path.join(DONTSTARVE_DIR, 'mega_log.txt'),
    maxBytes=20*1024*1024,
    backupCount=10,
))


def start():
    print("starting multiprocess for start server")
    MR = redis.Redis(decode_responses=True)
    COMMAND_ROOT = os.path.join(INSTALL_DIR, "bin64")
    cmd = os.path.join(COMMAND_ROOT, COMMAND)
    os.chdir(COMMAND_ROOT)
    command_line = [cmd, "-cluster", CLUSTER_NAME, "-shard", "Master"]
    MR.delete(REDIS_SERVER_COMMAND)
    MR.delete(REDIS_SERVER_STATE)
    add_server_mod_to_auto_update()
    master_p = subprocess.Popen(command_line, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
    command_line[-1] = "Caves"
    cave_p = subprocess.Popen(command_line,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
    MR.lpush(REDIS_SERVER_STATE, "starting")
    logger.info("server subprocess start")
    t_send = threading.Thread(target=send_console_command, args=(master_p,))
    t_send.daemon = True
    t_send.start()
    t_recieve_m = threading.Thread(target=get_output, args=(master_p,))
    t_recieve_m.daemon = True
    t_recieve_m.start()
    t_recieve_c = threading.Thread(target=get_output, 
            args=(cave_p,), kwargs={"master": False})
    t_recieve_c.daemon = True
    t_recieve_c.start()
    stopped = False
    while True:
        if stopped: 
            break
        if master_p.poll() is not None and cave_p.poll() is not None:
            MR.lpush(REDIS_SERVER_STATE, "idle")
            logger.info("Shutdown before command")
            break
        server_command = MR.get(REDIS_SERVER_COMMAND)
        if server_command == "stop":
            logger.info("get server command: stop")
            master_p.terminate()
            cave_p.terminate()
            MR.lpush(REDIS_SERVER_STATE, "shutting down")
            t_start_shut = time.time()
            timeout_shut = 20
            while True:
                if master_p.poll() is not None and cave_p.poll() is not None:
                    MR.lpush(REDIS_SERVER_STATE, "idle")
                    logger.info("Normal Shutdown")
                    stopped = True
                    break
                else:
                    t_now_shut = time.time()
                    if t_now_shut - t_start_shut >= timeout_shut:
                        master_p.send_signal(SIGINT)
                        master_p.send_signal(SIGINT)
                        MR.lpush(REDIS_SERVER_STATE, "idle")
                        logger.info("Force Interrupt")
                        stopped = True
                        break
                time.sleep(1)
        time.sleep(1)
    MR.delete(REDIS_SERVER_INFO)


def update():
    R = redis.Redis(decode_responses=True)
    os.chdir(STEAMCMD_DIR)
    p = subprocess.Popen(
        ("./steamcmd.sh", "+force_install_dir", INSTALL_DIR,
        "+login anonymous", "+app_update", "343050", "validate", "+quit"),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8"
    )
    logger.info("update start")
    os.chdir(CWD)
    phase = 0
    t_start = time.time()
    timeout = 240
    while True:
        line = p.stdout.readline()
        if "Checking for available updates" in line and phase == 0:
            phase = 1
            R.set(REDIS_UPDATE_STATE, "1/6")
        elif "Downloading update" in line and phase <= 1:
            phase = 2
            R.set(REDIS_UPDATE_STATE, "2/6")
        elif "Download Complete" in line and phase <= 2:
            phase = 3
            R.set(REDIS_UPDATE_STATE, "3/6")
        elif "Verifying installation" in line and phase <= 3:
            phase = 4
            R.set(REDIS_UPDATE_STATE, "4/6")
        elif "Update state" in line and phase <= 4:
            phase = 5
            R.set(REDIS_UPDATE_STATE, "5/6")
        elif "Success!" in line and phase <= 5:
            R.set(REDIS_UPDATE_STATE, "done")
            logger.info("update success")
            break
        elif "ERROR" in line and "ignore" not in line:
            logger.error(f"start ERROR: {line}")
            R.set(REDIS_UPDATE_STATE, "ERROR")
            break
        elif time.time() - t_start > timeout:
            logger.warning(f"not starting after {timeout}s")
            R.set(REDIS_UPDATE_STATE, "timeout")
            break
    p.communicate()
    logger.info("update process end")

def stop():
    r = redis.Redis(decode_responses=True)
    r.set(REDIS_SERVER_COMMAND, "stop")

def send_console_command(popen):
    MR = redis.Redis(decode_responses=True)
    MR.delete(REDIS_CONSOLE_COMAND)
    while True:
        msg = MR.brpop(REDIS_CONSOLE_COMAND)[1]
        logger.info(f'console get msg: {msg}')
        popen.stdin.write(msg+'\n')
        popen.stdin.flush()
        print("communicate complete")

def get_output(popen, master=True):
    lh = LineHandler()
    level = 'Master' if master else 'Caves'
    while True:
        try:
            out = popen.stdout.readline()
        except UnicodeDecodeError:
            continue
        else:
            if master:
                lh.handle(out)
            out = out.strip()
            if out:
                logger.info(f"[{level}]: {out}")

def dummy_redis_dec(name):
    def _decorator(func):
        def _dec(*args, **kwargs):
            print(f"executing dummy redis method {name}")
            ret = func(*args, **kwargs)
            return ret
        return _dec
    return _decorator

class DummyRedis:
    def __init__(self):
        self.methods = {}

    def __getattr__(self, name):
        if name not in self.methods:
            self.methods[name] = dummy_redis_dec(name)(self._dummy_method)
        return self.methods[name]
    
    def _dummy_method(self, name, *values):
        print(f"trying to operate key:{name} with values:{values}")
        return

class LineHandler:
    def __init__(self, use_redis=True):
        self.dt_start = datetime.datetime(year=1970, month=1, day=1, tzinfo=TZ)
        self.last_dt = self.dt_start
        self.days_passed = datetime.timedelta()
        self.starting = False
        self.curl_error_dt = None
        self.phase = -1
        self.last_chat_dt = None  # annoucement chat
        self.version = "unknown"
        self.rollback = False
        self.regen = False
        if use_redis is True:
            self.redis = redis.Redis(decode_responses=True)
        else:
            self.redis = DummyRedis()


    def handle(self, line):
        line = line.strip()
        content = line[12:]
        update_info = False
        if self.starting is True:
            if "Running main.lua" in line and self.phase == 0:
                self.phase = 1
                self.redis.lpush(REDIS_SERVER_STATE, "1/6")
                logger.info(f"start up phase {self.phase}")
            elif "Load FE: done" in line and self.phase == 1:
                self.phase = 2
                self.redis.lpush(REDIS_SERVER_STATE, "2/6")
                logger.info(f"start up phase {self.phase}")
            elif "Unload FE done" in line and self.phase == 2:
                self.phase = 3
                self.redis.lpush(REDIS_SERVER_STATE, "3/6")
                logger.info(f"start up phase {self.phase}")
            elif "LOAD BE" in line and self.phase == 3:
                self.phase = 4
                self.redis.lpush(REDIS_SERVER_STATE, "4/6")
                logger.info(f"start up phase {self.phase}")
            elif "LOAD BE: done" in line and self.phase == 4:
                self.phase = 5
                self.redis.lpush(REDIS_SERVER_STATE, "5/6")
                logger.info(f"start up phase {self.phase}")
            elif ("(active)" in line or "(disabled)" in line) \
                        and self.phase == 5:
                self.phase = 6
                self.redis.lpush(REDIS_SERVER_STATE, "running")
                logger.info("start up success")
                self.starting = False
                self.redis.lpush(REDIS_CONSOLE_COMAND, GET_SERVER_INFO_COMMAND)
                self.redis.lpush(REDIS_CONSOLE_COMAND, GET_PREFABS_COMMAND)
            elif "ERROR" in line:
                logger.error(f"STARTUP ERROR: {line}")
                self.redis.lpush(REDIS_SERVER_STATE, "ERROR")
                self.starting = False
            elif content.startswith("Current time"):
                match = START_TIME_PATTERN.search(line)
                if match:
                    dt_str = match.group("datetime")
                    dt = datetime.datetime.strptime(
                            dt_str+" +0800", 
                            "%a %b %d %X %Y %z"
                    )
                    t_delta = self._extract_deltatime_from_line(line)
                    self.dt_start = dt - t_delta
                    self.days_passed = datetime.timedelta()
                    self.last_dt = self.dt_start
                    logger.info(f"server start at {self.dt_start}")
                else:
                    logger.warning(f"start time miss: {line}")
            elif content.startswith("Version"):
                self.version = content[-6:]
            # to add world setting read
            return
        # start up handle end
        if content.startswith("[Say]") or content.startswith("[Whisper]"):
            match = CHAT_PATTERN.search(line)
            if match:
                ku = match.group("ku")
                name = match.group("name")
                msg = match.group("message")
                dt = self._get_current_time(line)
                message = MESSAGE_FORMAT.format(
                    datetime=dt.strftime("%m-%d %X"),
                    username=name,
                    msg=msg,
                )
                logger.info(f"[chat] ({ku}) [{name}]: {msg}")
                if msg and ord(msg[0]) == 57600:
                    # Announcement msg
                    # only push 1 msg to redis every 2 min
                    l_dt = self.last_chat_dt
                    if l_dt:
                        if dt - l_dt < datetime.timedelta(minutes=2):
                            return
                    self.last_chat_dt = dt
                self.redis.zadd(REDIS_CHAT, {message: int(dt.timestamp())})
        elif content.startswith("Client authenticated"):
            match = AUTH_PATTERN.search(line)
            if match:
                ku = match.group("ku")
                name = match.group("name").strip('\r')
                dt = self._get_current_time(line)
                ts = int(dt.timestamp())
                la_old_str = self.redis.hget(REDIS_KU_LA, ku)
                if la_old_str:
                    la_old = int(la_old_str)
                    if ts > la_old:
                        self.redis.hset(REDIS_KU_LA, ku, str(ts))
                        self.redis.hset(REDIS_KU_MAPPING, ku, name)
                else:
                    self.redis.hset(REDIS_KU_LA, ku, str(ts))
                    self.redis.hset(REDIS_KU_MAPPING, ku, name)
                logger.info(f"[user] {ku}: {name}")
        elif line.endswith("TokenPurpose"):
            # time sync, usually happens every 30 min
            dt = self._get_current_time(line)
            update_info = True
            logger.info(f"time sync at {dt}")
        elif content.startswith("CURL ERROR"):
            msg = "CURL ERROR in connecting to KLEI"
            dt = self._get_current_time(line)
            if self.curl_error_dt is None:
                self.curl_error_dt = dt
                logger.info(msg)
            else:
                if dt - self.curl_error_dt > datetime.timedelta(minutes=5):
                    self.curl_error_dt = dt
                    logger.info(msg)
                else:
                    logger.debug(msg)
        elif "ReceiveRemoteExecute" in content:
            m = REMOTE_COMMAND_PATTERN.search(content)
            if m:
                logger.info(content)
                ku = m.group("ku")
                name = m.group("name")
                content = m.group("content")
                cord = m.group("cord")
                cmd = self._translate_remote_command(content)
                logger.info(f"[execute] [({ku}) {name}] {cmd} @({cord})")
        elif content.startswith("Starting Up"):
            self.starting = True
            self.phase = 0
            logger.info("trying to go into start mode")
        elif content.startswith("Received world rollback"):
            match = ROLLBACK_PATTERN.search(content)
            if match:
                count = match.group("count")
                self.rollback = True
                self.redis.lpush(REDIS_SERVER_STATE, "rollback")
                logger.info(f"server rollback {count}")
        elif content.startswith("Received world reset"):
            self.redis.lpush(REDIS_SERVER_STATE, 'regenerate')
            self.regen = True
            logger.info(f"server regenerating")
        elif (self.rollback is True or self.regen is True) and \
                ("(active)" in line or "(disabled)" in line):
            self.redis.lpush(REDIS_SERVER_STATE, "running")
            update_info = True
            if self.rollback is True:
                self.rollback = False
                logger.info(f"server rollback success")
            elif self.regen is True:
                self.regen = False
                logger.info(f"server regenerate success")
        elif content.startswith("Shutting down"):
            logger.info("shutting down")
        elif content.startswith("Spawn request"):
            update_info = True
        elif content.startswith("Resuming user"):
            update_info = True
        elif content.startswith("[Leave Announcement]"):
            update_info = True
        elif content.startswith("Serializing world"):
            task = ('backup', 'backup_task_dummy_code')
            task_json = json.dumps(task)
            self.redis.rpush(REDIS_TASK_KEY, task_json)
            update_info = True
        elif content.startswith("[server status]"):
            status_json = content[16:]
            try:
                server_info = json.loads(status_json)
                info = self._translate_server_info(server_info)
            except json.JSONDecodeError:
                logger.warning(f"cant parse to json:{status_json}")
            else:
                print(info)
                self.redis.set(REDIS_SERVER_INFO, info, ex=2100)
        elif content.startswith("[prefab]"):
            prefab_def = content[9:]
            prefab, name = prefab_def.strip().split(":")
            if name:
                self.redis.hset(REDIS_PREFABS, prefab, name)
        else:
            pass
        if update_info:
            self.redis.lpush(REDIS_CONSOLE_COMAND, GET_SERVER_INFO_COMMAND)
    
    def _get_current_time(self, line):
        t_delta = self._extract_deltatime_from_line(line)
        dt = self.dt_start + t_delta + self.days_passed
        if self.last_dt - dt > datetime.timedelta(minutes=20):
            dt = dt + datetime.timedelta(days=1)
            self.days_passed += datetime.timedelta(days=1)
            logger.info(f"day passed {self.days_passed} since {self.dt_start}")
        self.last_dt = dt
        return dt
    
    def _translate_server_info(self, server_info):
        """
        {
            'server_name': '来吧来吧1558', 
            'max_players': '6', 
            'game_mode': 'survival', 
            'daysinseason': 8, 
            'season': 'winter', 
            'days': 28, 
            'player_list': [
                {
                    'name': '[Host]', 
                    'prefab': '', 
                    'playerage': 0, 
                    'steamid': 'nil', 
                    'userid': 'KU_3RvV9haR', 
                    'admin': True
                }, {
                    'name': 'Besiege', 
                    'prefab': '', 
                    'playerage': 0, 
                    'steamid': '76561198192802721', 
                    'userid': 'KU_3RvV9haR', 
                    'admin': True}
            ]
        }
        """
        SEASON = {"spring": "春", "summer": "夏", "autumn": "秋", "winter": "冬"}
        _players = server_info.get("player_list", [])
        players = []
        for p in _players:
            if p['steamid'] == "nil":
                # server itself consider as a player but steamid is nil
                continue
            prefab = PREFABS.get(p['prefab']) or p['prefab']
            player = ("*" if p['admin'] else "") + f"{p['name']} ({prefab})"
            players.append(player)
        if players:
            num_players = len(players)
        else:
            num_players = 0
        season = SEASON.get(server_info["season"], "未知")
        daysinseason = server_info["daysinseason"] + 1
        days = server_info["days"] + 1
        info = f"""服务器名:\n    {server_info["server_name"]}\n""" + \
            f"""玩家: {num_players}/{server_info["max_players"]}\n""" + \
            f"""天数: {days}\n""" + \
            f"""季节: {season} {daysinseason}\n""" + \
            f"""版本: {self.version}"""
        if players:
            info += "\n"+"玩家列表:\n  "+ "\n  ".join(players)
        return info
    
    @staticmethod
    def _translate_remote_command(cmd):
        for ptn_name, ptn in PTNS.items():
            pattern = ptn['pattern']
            match = pattern.search(cmd)
            if match:
                player_ku = None
                if ptn.get("has_player"):
                    match_player = FPTN.search(cmd)
                    if match_player:
                        player_ku = match_player.group("ku")
                return f"{ptn_name}" + (f" on {player_ku}" if player_ku else "")
        else:
            return "unknown command pattern"

    
    @staticmethod
    def _extract_deltatime_from_line(line):
        match_time = TIME_PATTERN.search(line)
        hours = int(match_time.group("hour"))
        minutes = int(match_time.group("minute"))
        seconds = int(match_time.group("second"))
        return datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)


def main():
    R = redis.Redis(decode_responses=True)
    R.delete(REDIS_QBOT_COMMAND)
    p_server = None
    while True:
        logger.info("listening for request")
        _, msg = R.brpop(REDIS_QBOT_COMMAND)
        logger.info(f"get qbot command {msg}")
        if msg == "start":
            if p_server is None or not p_server.is_alive():
                p_server = mp.Process(target=start)
                p_server.start()
                logger.info(f"get task start server{p_server.pid}: success")
            else:
                R.lpush(REDIS_SERVER_STATE, "start stuck")
                logger.info("get task start server: stuck")
        elif msg == "update":
            t = mp.Process(target=update)
            t.start()
            logger.info("get task update server")
        elif msg == "stop":
            stop()
            logger.info("get task stop server")
        else:
            logger.warning(f"get unidentified task: {msg}")


if __name__ == "__main__":
    try:
        main()
    except (SystemExit, KeyboardInterrupt):
        logger.info("interactive server exit")