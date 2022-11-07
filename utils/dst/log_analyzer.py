import re
import os
import datetime
import time
import logging

import redis
# analyze log in dst

REDIS_KU_MAPPING = "dst:user:ku"
REDIS_KU_LA = "dst:user:lastaccess"
REDIS_SERVER_STATE = "dst:state:server"
CWD = os.path.dirname(__file__)
AUTH_PATTERN = re.compile("Client authenticated: \((?P<ku>[\w\d\-_]+)\) (?P<name>.+)$")
IP_PATTERN = re.compile("New incoming connection (?P<ip>[\d+.]+)\|\d+ <(?P<uid>\d+)>$")
START_TIME_PATTERN = re.compile("Current time: (?P<datetime>.+)")
TIME_PATTERN = re.compile("^\[(?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+)\]")
TZ = datetime.timezone(datetime.timedelta(hours=8), name="Asia/Shanghai")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

# class implement
class LogAnalyzer:
    def __init__(self, log_path, realtime=False):
        self.log_path = log_path
        self.fp = open(log_path, 'r', errors='ignore')
        self.stmt = os.stat(self.log_path).st_mtime
        self.dt_start = datetime.datetime.fromtimestamp(
            self.stmt,
            tz=TZ
        )
        self.days_passed = datetime.timedelta()
        self.last_dt = self.dt_start
        self.redis = redis.Redis(decode_responses=True)
        self.fp_pos = self.fp.tell()
        self.start_up = False
        self.realtime = realtime
    
    def start(self):
        # realtime means affect redis and loop until interrupt
        self._start()
        if self.realtime:
            time.sleep(2)
            self.stmt = os.stat(self.log_path).st_mtime
            while True:
                time.sleep(5)
                if self.stmt == os.stat(self.log_path).st_mtime:
                    logger.debug("waiting for log file change")
                    continue
                else:
                    logger.info("log file change")
                    self.reopen()
                    self.stmt = os.stat(self.log_path).st_mtime
                    self.fp_pos = self.fp.tell()
                    self._start()

    def _start(self):
        while True:
            line = self.fp.readline()
            if line == "" or not line.endswith('\n'):
                logger.debug(f"continue read for line:{line}")
                if self.realtime:
                    time.sleep(3)
                    self.fp.seek(self.fp_pos)
                    continue
                else:
                    break
            line = line.strip()
            # starting up condition
            if self.start_up and self.realtime:
                if "Running main.lua" in line and phase == 1:
                    phase = 2
                    self.redis.set(REDIS_SERVER_STATE, "2/4")
                    logger.info("start up 2/4")
                elif "Account Communication Success" in line and phase == 2:
                    phase = 3
                    self.redis.set(REDIS_SERVER_STATE, "3/4")
                    logger.info("start up 3/4")
                elif ("(active)" in line or "(disabled)" in line) \
                            and phase == 3:
                    phase = 4
                    self.redis.set(REDIS_SERVER_STATE, "running")
                    logger.info("start up success")
                    self.start_up = False
                elif "ERROR" in line:
                    logger.error(f"STARTUP ERROR: {line}")
                    self.redis.set(REDIS_SERVER_STATE, "ERROR")
                    self.start_up = False
                    logger.info("start up ERROR")
                self.fp_pos = self.fp.tell()
                continue
            # before start up or after started
            if "Client authenticated" in line:
                match = AUTH_PATTERN.search(line)
                if match:
                    ku = match.group("ku")
                    name = match.group("name").strip('\r')
                    dt = self._get_current_time(line)
                    ts = int(dt.timestamp())
                    la_old_str = self.redis.hget(REDIS_KU_LA, ku)
                    if la_old_str:
                        la_old = int(la_old_str)
                        if ts <= la_old:
                            continue
                    self.redis.hset(REDIS_KU_LA, ku, str(ts))
                    self.redis.hset(REDIS_KU_MAPPING, ku, name)
                    logger.info(f"[user] {ku}: {name}")
            elif "Current time" in line:
                # server start time
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
                    logger.info(f"server start at {dt} with offset {t_delta}")
                else:
                    logger.info(f"unmatched start time line: {line}")
                    continue
                now = datetime.datetime.now(tz=TZ)
                throat_diff = datetime.timedelta(minutes=2)
                if now - self.dt_start < throat_diff:
                    # consider log as real realtime
                    self.start_up = True
                    phase = 1
                    logger.info("start up 1/4")
                else:
                    logger.info(f"{now} much more newer than {self.dt_start}")
                    logger.info(f"wont really go into start mode")
                    self.start_up = False
                    phase = 0
            elif line.endswith("TokenPurpose"):
                # time sync, usually happens every 30 min
                dt = self._get_current_time(line)
                logger.info(f"time sync at {dt}")
            elif line[12:].startswith("CURL ERROR"):
                logger.debug("CURL ERROR in connecting to KLEI")
            elif self.realtime and line[12:].startswith("Starting Up"):
                logger.info("trying to go into start mode")
            elif self.realtime and line[12:].startswith("Shutting down"):
                logger.info("shutting down")
                break
            else:
                pass
            self.fp_pos = self.fp.tell()
    
    def reopen(self):
        self.fp.close()
        self.fp = open(self.log_path, 'r', errors='ignore')
    
    def _is_deprecated(self, line):
        # time in line earlier than now more than 2 min consider deprecated
        dt = self._get_current_time(line)
        dt_now = datetime.datetime.now(tz=TZ)
        if dt_now - dt > datetime.timedelta(minutes=2):
            return True
        return False
        
    def _get_current_time(self, line):
        t_delta = self._extract_deltatime_from_line(line)
        dt = self.dt_start + t_delta + self.days_passed
        if self.last_dt - dt > datetime.timedelta(minutes=20):
            dt = dt + datetime.timedelta(days=1)
            self.days_passed += datetime.timedelta(days=1)
            logger.info(f"day passed {self.days_passed} since {self.dt_start}")
        self.last_dt = dt
        return dt

    @staticmethod
    def _extract_deltatime_from_line(line):
        match_time = TIME_PATTERN.search(line)
        hours = int(match_time.group("hour"))
        minutes = int(match_time.group("minute"))
        seconds = int(match_time.group("second"))
        return datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)

    def __del__(self):
        self.fp.close()


# function implement
# def analyze(log_path):
#     R = redis.Redis()
#     with open(log_path, 'rb') as fp:
#         ku_dict = {}
#         ip = ""
#         uid = ""
#         ip_lineno = 0
#         dt_start = datetime.datetime(2000,1,1)
#         days_passed = 0  # after pass 1 day or more, the dt offset to add
#         last_dt = 0
#         for lineno, b_line in enumerate(fp):
#             try:
#                 line = b_line.decode("utf8", errors='ignore')
#             except UnicodeDecodeError:
#                 continue
#             line = line.strip()
#             if AUTH_PATTERN.search(line):
#                 match = AUTH_PATTERN.search(line)
#                 ku = match.group("ku")
#                 name = match.group("name").strip('\r')
#                 R.hset(REDIS_KU_MAPPING, ku, name)
#                 logger.info(f"[user] {ku}: {name}")
#                 if ku in ku_dict:
#                     name_list = ku_dict[ku]['name_list']
#                     ip_list = ku_dict[ku]["ip_list"]
#                     uid_list = ku_dict[ku]["uid_list"]
#                     if name not in name_list:
#                         name_list.append(name)
#                     if ip not in ip_list:
#                         ip_list.append(ip)
#                     if uid not in uid_list:
#                         uid_list.append(uid)
#                 else:
#                     ku_dict[ku] = {
#                         'name_list':[name],
#                         'ip_list':[ip],
#                         'uid_list':[uid],
#                     }
#                 ip = ""
#                 uid = ""
#                 if lineno - ip_lineno > 20:
#                     print(f"[WARN]match line:{ip_lineno} with line:{lineno}")
#             elif IP_PATTERN.search(line):
#                 match = IP_PATTERN.search(line)
#                 ip = match.group("ip")
#                 uid = match.group("uid")
#                 ip_lineno = lineno
#             elif "Current time" in line:
#                 # server start time
#                 match = START_TIME_PATTERN.search(line)
#                 if match:
#                     dt_str = match.group("datetime")
#                     dt = datetime.datetime.strptime(
#                             dt_str+" +0800", 
#                             "%a %b %d %X %Y %z"
#                     )
#                     t_delta = _extract_deltatime_from_line(line)
#                     dt_start = dt - t_delta
#                     days_passed = 0
#                     last_dt = dt_start
#                     logger.info(f"server start at {dt} with offset {t_delta}")
#             elif line.endswith("TokenPurpose"):
#                 # time sync, usually happens every 30 min
#                 t_delta = _extract_deltatime_from_line(line)
#                 dt = dt_start + t_delta + datetime.timedelta(days=days_passed)
#                 if last_dt - dt > datetime.timedelta(minutes=20):
#                     dt = dt + datetime.timedelta(days=1)
#                     days_passed += 1
#                     logger.info(f"day passed {days_passed} since {dt_start}")
#                 last_dt = dt
#                 logger.info(f"time sync at {dt}")
#             elif line[12:].startswith("CURL ERROR"):
#                 logger.debug("CURL ERROR in connecting to KLEI")
#             else:
#                 pass
#     return ku_dict


# def _extract_deltatime_from_line(line):
#     match_time = TIME_PATTERN.search(line)
#     hours = int(match_time.group("hour"))
#     minutes = int(match_time.group("minute"))
#     seconds = int(match_time.group("second"))
#     return datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)

# def merge_ku_dict(*ku_ds):
#     result = {}
#     for ku_d in ku_ds:
#         for ku, record in ku_d.items():
#             record_total = result.setdefault(ku, {})
#             for info in ('ip_list', 'name_list', 'uid_list'):
#                 total = record_total.get(info, [])
#                 record_total[info] = list(
#                     set(total).union(record[info])
#                 )
#     return result


# def recursive_scan(dir):
#     ds = []
#     for entry in os.scandir(dir):
#         if entry.is_file() and entry.name.startswith("server_log"):
#             ds.append(analyze(entry.path))
#         elif entry.is_dir():
#             ds.extend(recursive_scan(entry.path))
#     return ds


# def temp():
#     cwd = os.path.dirname(__file__)
#     # ds = recursive_scan(cwd)
#     # kud = merge_ku_dict(*ds)
#     import json
#     # with open(os.path.join(cwd, 'ku_dict.json'), 'w') as fp:
#     #     json.dump(kud, fp, ensure_ascii=False, indent=2)
#     p1 = '/home/hikaru/qqbot/utils/dst/manage_server/ku_dict.json'
#     p2 = '/home/hikaru/.klei/DoNotStarveTogether/ku_dict.json'
#     with open(p1, 'r') as fp:
#         ku_d1 = json.load(fp)
#     with open(p2, 'r') as fp:
#         ku_d2 = json.load(fp)
#     ku_d = merge_ku_dict(ku_d1, ku_d2)
#     with open(os.path.join(cwd, 'total_ku.json'), 'w') as fp:
#         json.dump(ku_d, fp, ensure_ascii=False, indent=2)

def main():
    log_path = os.path.join(CWD, 'manage_server/log.txt')
    ana = LogAnalyzer(log_path, realtime=True)
    ana.start()


if __name__ == "__main__":
    main()