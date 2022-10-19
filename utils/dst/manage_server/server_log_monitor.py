import time
import redis

REDIS_CHANNEL = "dst:channel:server"
REDIS_PID_M = "dst:pid:master"
REDIS_PID_C = "dst:pid:caves"
REDIS_SERVER_STATE = "dst:state:server"
REDIS_UPDATE_STATE = "dst:update:server"

MR = redis.Redis(decode_responses=True)

def main():
    log_loc = "log.txt"
    waiting_for_start = False
    timeout = 120
    with open(log_loc, 'r') as fp:
        while True:
            for line in fp:
                if "Starting Up" in line and phase == 0:
                    phase = 1
                    MR.set(REDIS_SERVER_STATE, "1/4")
                    waiting_for_start = True
                    t_start = time.time()
                elif "Running main.lua" in line and phase == 1:
                    phase = 2
                    MR.set(REDIS_SERVER_STATE, "2/4")
                elif "Account Communication Success" in line and phase == 2:
                    phase = 3
                    MR.set(REDIS_SERVER_STATE, "3/4")
                elif ("(active)" in line or "(disabled)" in line) and phase == 3:
                    phase = 4
                    MR.set(REDIS_SERVER_STATE, "running")
                    print("start success")
                    waiting_for_start = False
                elif "ERROR" in line:
                    print("start ERROR:", line)
                    MR.set(REDIS_SERVER_STATE, "ERROR")
                    waiting_for_start = False
                elif "Shutting down" in line:
                    print("server stopped:", line)
                    MR.set(REDIS_SERVER_STATE, "idle")
                    waiting_for_start = False
                else:
                    if waiting_for_start:
                        t_now = time.time()
                        if t_now - t_start >= timeout:
                            MR.set(REDIS_SERVER_STATE, "setup timeout")
            time.sleep(1)
