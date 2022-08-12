import configparser
import os
import subprocess
from signal import SIGTERM, SIGINT
import threading
import time
import sys
import multiprocessing as mp

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
R = redis.Redis(decode_responses=True)
REDIS_CHANNEL = "dst:channel:server"
REDIS_PID_M = "dst:pid:master"
REDIS_PID_C = "dst:pid:caves"
REDIS_SERVER_STATE = "dst:state:server"
REDIS_UPDATE_STATE = "dst:update:server"


def _mp_server():
    """start server in multiprocess
    and also handle stopping it
    """
    fd = open("log.txt", 'w')
    MR = redis.Redis(decode_responses=True)
    print("starting multiprocess for start server")
    COMMAND_ROOT = os.path.join(INSTALL_DIR, "bin64")
    cmd = os.path.join(COMMAND_ROOT, COMMAND)
    os.chdir(COMMAND_ROOT)
    command_line = [cmd, "-cluster", CLUSTER_NAME, "-shard", "Master"]
    master_p = subprocess.Popen(command_line,
        stdout=fd, stderr=subprocess.STDOUT, encoding="utf8")
    command_line[-1] = "Caves"
    cave_p = subprocess.Popen(command_line,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, encoding="utf8")
    print("server subprocess start")
    t_start = time.time()
    timeout = 120
    stop_it_now = False
    phase = 0
    start_over = False
    # while True:
    #     if start_over:
    #         break
    #     for line in master_p.stdout:
    #         if "Starting Up" in line and phase == 0:
    #             phase = 1
    #             MR.set(REDIS_SERVER_STATE, "1/4")
    #         elif "Running main.lua" in line and phase == 1:
    #             phase = 2
    #             MR.set(REDIS_SERVER_STATE, "2/4")
    #         elif "Account Communication Success" in line and phase == 2:
    #             phase = 3
    #             MR.set(REDIS_SERVER_STATE, "3/4")
    #         elif ("(active)" in line or "(disabled)" in line) and phase == 3:
    #             phase = 4
    #             MR.set(REDIS_SERVER_STATE, "running")
    #             print("start success")
    #             start_over = True
    #             break
    #         elif "ERROR" in line:
    #             print("start ERROR:", line)
    #             MR.set(REDIS_SERVER_STATE, "ERROR")
    #             stop_it_now = True
    #             start_over = True
    #             break
    #         else:
    #             t_now = time.time()
    #             if t_now - t_start >= timeout:
    #                 MR.set(REDIS_SERVER_STATE, "setup timeout")
    #                 start_over = True
    #                 break
    MR.set(REDIS_SERVER_STATE, "running")  # tmp line should be delete later
    stopped = False
    print("""listen for stopping server""")
    while True:
        if stopped:
             break
        server_state = MR.get(REDIS_SERVER_STATE)
        # print(f"state: {server_state}")
        if server_state == "stopping" or stop_it_now:
            stopped = True
            print("trying terminate")
            master_p.terminate()
            cave_p.terminate()
            print("testing if terminate success")
            t_start_shut = time.time()
            timeout_shut = 20
            while True:
                m_state = master_p.poll()
                c_state = cave_p.poll()
                if m_state is not None and c_state is not None:
                    MR.set(REDIS_SERVER_STATE, "idle")
                    print("Normal Shutdown")
                    break
                else:
                    t_now_shut = time.time()
                    if t_now_shut - t_start_shut >= timeout_shut:
                        master_p.send_signal(SIGINT)
                        cave_p.send_signal(SIGINT)
                        MR.set(REDIS_SERVER_STATE, "idle")
                        print("Force Interrupt")
                        break
                time.sleep(1)
        time.sleep(1)
    fd.close()



def start_server():
    print("starting")
    p = mp.Process(target= _mp_server)
    p.start()
    # cave_p.wait()
    # master_p.wait()
    # os.chdir(CWD)
    # with open("master_log.txt", "w") as log:
    #     log.write(master_p.stdout.read())
    # with open("caves_log.txt", "w") as log:
    #     log.write(cave_p.stdout.read())


def stop_server():
    print("stopping")
    R.set(REDIS_SERVER_STATE, "stopping")


def update_server():
    os.chdir(STEAMCMD_DIR)
    p = subprocess.Popen(
        ("./steamcmd.sh", "+force_install_dir", INSTALL_DIR,
        "+login anonymous", "+app_update", "343050", "validate", "+quit"),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8"
    )
    print("update start")
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
            elif "ERROR" in line and "ignore" not in line:
                print("start ERROR:", line)
                R.set(REDIS_UPDATE_STATE, "ERROR")
                return
            elif i > 1500:
                print("not starting after so many lines")
                return
    print("update end")
    # with open("update.log", 'w') as log:
    #     log.write(p.stdout.read())


def main():
    p = R.pubsub()
    p.subscribe(REDIS_CHANNEL)
    print("listening for request")
    for msg in p.listen():
        if msg['type'] == 'message':
            data = msg['data']
            if data == 'start':
                print("starting server")
                t = mp.Process(target=start_server)
                t.start()
            elif data == 'stop':
                print("stopping server")
                t = mp.Process(target=stop_server)
                t.start()
            elif data == 'update':
                print("updating server")
                t = mp.Process(target=update_server)
                t.start()
            elif data == 'fin':
                return
            else:
                pass


if __name__ == "__main__":
    main()
