import configparser
import os
import subprocess
from signal import SIGTERM
import threading

import redis


CONFIG = configparser.ConfigParser()
CONFIG.read("server.ini")
STEAM = CONFIG['steam']
DONTSTARVE = CONFIG['dontstarve']

HOME = STEAM['home']
STEAMCMD_DIR = os.path.join(HOME, STEAM['steamcmd_dir'])
INSTALL_DIR = os.path.join(HOME, DONTSTARVE['install_dir'])
CLUSTER_NAME = DONTSTARVE['cluster_name']
DONTSTARVE_DIR = os.path.join(HOME, DONTSTARVE['dontstarve_dir'])
COMMAND = "dontstarve_dedicated_server_nullrenderer_x64"
CWD = os.getcwd()
R = redis.Redis()
REDIS_CHANNEL = "dst:channel:server"
REDIS_PID_M = "dst:pid:master"
REDIS_PID_C = "dst:pid:caves"
REDIS_SERVER_STATE = "dst:state:server"
REDIS_UPDATE_STATE = "dst:update:server"

def start_server():
    COMMAND_ROOT = os.path.join(INSTALL_DIR, "bin64")
    cmd = os.path.join(COMMAND_ROOT, COMMAND)
    os.chdir(COMMAND_ROOT)
    command_line = [cmd, "-cluster", CLUSTER_NAME, "-shard", "Caves"]
    cave_p = subprocess.Popen(command_line,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
    R.set(REDIS_PID_C, cave_p.pid)
    command_line[-1] = "Master"
    master_p = subprocess.Popen(command_line,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
    R.set(REDIS_PID_M, master_p.pid)
    R.set(REDIS_SERVER_STATE, "starting")
    phase = 0
    while True:
        for i, line in enumerate(master_p.stdout):
            if "Starting Up" in line and phase == 0:
                phase = 1
                R.set(REDIS_SERVER_STATE, "1/4")
            elif "Running main.lua" in line and phase == 1:
                phase = 2
                R.set(REDIS_SERVER_STATE, "2/4")
            elif "Account Communication Success" in line and phase == 2:
                phase = 3
                R.set(REDIS_SERVER_STATE, "3/4")
            elif ("(active)" in line or "(disabled)" in line) and phase == 3:
                phase = 4
                R.set(REDIS_SERVER_STATE, "running")
                print("start success")
                return
            elif "ERROR" in line:
                print("start ERROR:", line)
                R.set(REDIS_SERVER_STATE, "ERROR")
                return
            elif i > 1500:
                print("not starting after so many lines")
                return
    # cave_p.wait()
    # master_p.wait()
    # os.chdir(CWD)
    # with open("master_log.txt", "w") as log:
    #     log.write(master_p.stdout.read())
    # with open("caves_log.txt", "w") as log:
    #     log.write(cave_p.stdout.read())


def stop_server():
    R.set(REDIS_SERVER_STATE, "stopping")
    pid_m = int(R.get(REDIS_PID_M))
    pid_c = int(R.get(REDIS_PID_C))
    os.kill(pid_m, SIGTERM)
    os.kill(pid_c, SIGTERM)
    try:
        os.waitpid(pid_m, 0)
        os.waitpid(pid_c, 0)
    except OSError:  # occurs when pid has been stopped
        pass
    R.delete(REDIS_PID_C, REDIS_PID_M)
    R.set(REDIS_SERVER_STATE, "idle")
    print("server stopped")


def update_server():
    os.chdir(STEAMCMD_DIR)
    p = subprocess.Popen(
        ("./steamcmd.sh", "+force_install_dir", INSTALL_DIR,
        "+login anonymous", "+app_update", "343050", "validate", "+quit"),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8"
    )
    print("udpate start")
    os.chdir(CWD)
    phase = 0
    while True:
        for i, line in enumerate(p.stdout):
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
                return
            elif "ERROR" in line:
                print("start ERROR:", line)
                R.set(REDIS_UPDATE_STATE, "ERROR")
                return
            elif i > 1500:
                print("not starting after so many lines")
                return
    print("udpate end")
    # with open("update.log", 'w') as log:
    #     log.write(p.stdout.read())


def main():
    p = R.pubsub()
    p.subscribe(REDIS_CHANNEL)
    for msg in p.listen():
        if msg['type'] == 'message':
            data = msg['data'].decode('utf8')
            if data == 'start':
                print("starting server")
                t = threading.Thread(target=start_server)
                t.start()
            elif data == 'stop':
                print("stopping server")
                t = threading.Thread(target=stop_server)
                t.start()
            elif data == 'update':
                print("updating server")
                t = threading.Thread(target=update_server)
                t.start()
            elif data == 'fin':
                return
            else:
                pass


if __name__ == "__main__":
    main()
