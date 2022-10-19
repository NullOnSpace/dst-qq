#!/usr/bin/env python3
# edit cluster.ini
"""
todo:
edit() 改为可从命令行读取参数
添加成功反馈
"""

import configparser
import os.path
import sys


SETTING_DICT = {
    "GAMEPLAY": ("game_mode", "max_players", "pvp", "pause_when_empty"),
    "NETWORK": ("cluster_description", "cluster_name", "cluster_intention", "cluster_password"),
    "MISC": ("console_enabled",),
    "SHARD": ("shard_enabled", "bind_ip", "master_ip", "master_port", "cluster_key"),
}
SETTING_MAP = {}
for k, vs in SETTING_DICT.items():
    for v in vs:
        SETTING_MAP[v] = k
CONFIG_SERVER = configparser.ConfigParser()
CONFIG_SERVER.read("server.ini")
try:
    CLUSTER_DIR = os.path.join(
        CONFIG_SERVER['steam']['home'],
        CONFIG_SERVER['dontstarve']['dontstarve_dir'],
        CONFIG_SERVER['dontstarve']['cluster_name'],
        'cluster.ini'
    )
except KeyError as e:
    print(f"{e} in edit_settings")
    sys.exit(1)
CONFIG_CLUSTER = configparser.ConfigParser()
CONFIG_CLUSTER.read(CLUSTER_DIR)

def print_config():
    for section in CONFIG_CLUSTER:
        for key in CONFIG_CLUSTER[section]:
            print(f"{section}: {key}: {CONFIG_CLUSTER[section][key]}")

def edit(config, change, loc=CLUSTER_DIR):
    # change should be a dict like {"cluster_name": "new name"}
    for k, v in change.items():
        if k in SETTING_MAP:
            section = SETTING_MAP[k]
            config[section][k] = v
    with open(loc, 'w') as fp:
        config.write(fp)

def main():
    edit(CONFIG_CLUSTER, {"cluster_name": "brand new world"})


if __name__ == '__main__':
    main()
