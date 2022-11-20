#!/usr/bin/env python3
# edit cluster.ini

import configparser
import os.path
import sys

CWD = os.path.dirname(__file__)
sys.path.append(CWD)
from get_config import CLUSTER_DIR

CLUSTER_INI_PATH = os.path.join(CLUSTER_DIR, "cluster.ini")

SETTING_DICT = {
    "GAMEPLAY": ("game_mode", "max_players", "pvp", "pause_when_empty"),
    "NETWORK": ("cluster_description", "cluster_name", "cluster_intention", "cluster_password", "cluster_language"),
    "MISC": ("console_enabled",),
    "SHARD": ("shard_enabled", "bind_ip", "master_ip", "master_port", "cluster_key"),
}
SETTING_MAP = {}  # mapping option to its section
for k, vs in SETTING_DICT.items():
    for v in vs:
        SETTING_MAP[v] = k

def print_config(cluster_ini=CLUSTER_INI_PATH, exclude=('steam',)):
    config = configparser.ConfigParser()
    config.read(cluster_ini)
    res = "服务器设置:"
    for section in config:
        if section not in exclude:
            res += f"\n{section}"
            for key in config[section]:
                res += f"\n\t{key} = {config[section][key]}"
    return res

def edit(change, loc=CLUSTER_INI_PATH):
    # read from `config_path` change option in `change` then write to `loc`
    # change should be a dict like {"cluster_name": "new name"}
    config = configparser.ConfigParser()
    config.read(loc)
    errors = []
    for k, v in change.items():
        if k in SETTING_MAP:
            section = SETTING_MAP[k]
            config[section][k] = v
        else:
            errors.append(k)
    with open(loc, 'w') as fp:
        config.write(fp)
    return errors

def main():
    edit({"cluster_name": "brand new world"})
    print_config(CLUSTER_INI_PATH)


if __name__ == '__main__':
    main()
