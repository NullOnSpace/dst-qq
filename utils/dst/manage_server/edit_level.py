#!/usr/bin/#!/usr/bin/env python3
"""
read level settings and edit it
"""


import os
import sys
import configparser
import io
import zipfile

cwd = os.path.dirname(__file__)
sys.path.append(cwd)
import parse_lua as PL
from get_config import DONTSTARVE_DIR, CLUSTER_DIR, SCRIPT_FILE


MAP_NAME = "scripts/map/customize.lua"

CLUSTER_MAPPING = {
    "Master": "forest",
    "Caves": "cave",
}


def _end_read_settings(line):
    if "WORLDSETTINGS_MISC" in line:
        return True
    return False


def read_level_settings():
    # read level setting from dst scripts
    lp = PL.LUAParser(global_=PL.LUA_BUILTINS)
    with zipfile.ZipFile(SCRIPT_FILE) as zip:
        content = zip.read("scripts/map/customize.lua")
    fp = io.StringIO(content.decode("utf8"))
    lp.parse_lua(lua_file=fp, end_cond=_end_read_settings)
    result = {}
    for k, v in lp.global_.items():
        if k.endswith("GROUP") or k.endswith("MISC") and \
                not k.startswith("MOD_"):
            result[k] = v
    return result


def read_level_override(cluster="Master"):
    path = os.path.join(CLUSTER_DIR, cluster, "leveldataoverride.lua")
    if os.path.exists(path):
        with open(path, 'r') as fp:
            lp = PL.LUAParser(global_=PL.LUA_BUILTINS)
            lp.parse_lua(fp)
        override = lp.global_['__rt']
        return override
    else:
        return None


def fetch_item_settings(item):
    # for given item, return all valid settings in list
    # if item is misc return []
    # if item not a valid item, return None
    settings = read_level_settings() 
    for k, v in settings.items():
        if item in v:  # misc
            return []
        elif type(v) is PL.LuaDict:
            for cate, detail in v.items():
                if item in detail['items']:
                    desc = detail['items'][item].get("desc", detail['desc'])
                    return [d['data'] for d in desc]
    return None


def fetch_item_override(item, cluster="Master"):
    # fetch specified item's setting in server leveldataoverride
    override = read_level_override(cluster=cluster)
    if override:
        overrides = override['overrides']
        return overrides.get(item, False)  # False if item not exist
    else:
        return None  # path not exist


def rewrite_item(item, value, cluster="Master"):
    override = read_level_override(cluster=cluster)
    if override:
        valid_values = fetch_item_settings(item)
        if valid_values is None:
            return False, f'No such item:{item}'
        if value in valid_values:
            override['overrides'][item] = value
            PL.LUA_dump(override)
            path = os.path.join(CLUSTER_DIR, cluster, "leveldataoverride.lua")
            write_to_override(override, path)
            return True
        else:
            return False, f'{value} not in: {valid_values}'
    else:
        return False, 'level data override file path not exists'


def write_to_override(override, path):
    or_ = PL.LUA_dump(override)
    with open(path, 'w') as fp:
        fp.write("return ")
        fp.write(or_)


if __name__ == "__main__":
    OR = read_level_override()
    LS = read_level_settings()
    print(fetch_item_override('krampus'))
    print(fetch_item_settings('krampus'))
    rewrite_item('krampus', 'often')
    print(fetch_item_override('krampus'))
