#!/usr/bin/#!/usr/bin/env python3
"""
read level settings and edit it
"""
import os
import sys
import io
import zipfile
import json

import redis

cwd = os.path.dirname(__file__)
sys.path.append(cwd)
import parse_lua as PL
from get_config import DONTSTARVE_DIR, CLUSTER_DIR, SCRIPT_FILE
from parse_lua import REDIS_TRANSLATIONS_PREPEND as RTP


MAP_NAME = "scripts/map/customize.lua"
REDIS_SETTING_CUSTOMIZATION = RTP + "STRINGS.UI.CUSTOMIZATIONSCREEN"

CLUSTER_MAPPING = {
    "Master": "forest",
    "Caves": "cave",
}


def is_translated(s):
    return any(map(lambda x: ord(x)>255, s))

def item_to_str(item, key):
    R = redis.Redis(decode_responses=True)
    k = RTP+key
    item_json = R.hget(k, item.upper())
    if item_json:
        item_dict = json.loads(item_json)
        return item_dict['msgstr']


def str_to_item(s, key):
    R = redis.Redis(decode_responses=True)
    k = RTP+key
    items_dict = R.hgetall(k)
    for item, item_json in items_dict.items():
        item_dict = json.loads(item_json)
        if s == item_dict['msgstr']:
            return item.lower()


def get_transalted_items_dict():
    R = redis.Redis(decode_responses=True)
    setting_items_dict = R.hgetall(REDIS_SETTING_CUSTOMIZATION)
    d = dict()
    for item, item_json in setting_items_dict.items():
        item_dict = json.loads(item_json)
        msgstr = item_dict['msgstr']
        msgid = item_dict['msgid']
        d[msgstr] = {'id': msgid, 'item': item.lower()}
    return d

def get_closest_item(item):
    transed_items = get_transalted_items_dict()
    if item in transed_items:
        return transed_items[item]['item']
    else:
        return [transed_items[k]['item'] 
                    for k in transed_items if set(k).intersection(set(item))]


def _end_read_settings(line):
    if "MOD_WORLDSETTINGS_MISC" in line:
        return True
    return False


def read_level_settings():
    # read level setting from dst scripts
    STRINGS = PL.LazyText("STRINGS")
    class startlocations:
        GetGenStartLocations = [
            dict(text=STRINGS.UI.SANDBOXMENU.DEFAULTSTART, data="default"),
            dict(text=STRINGS.UI.SANDBOXMENU.PLUSSTART, data="plus"),
            dict(text=STRINGS.UI.SANDBOXMENU.DARKSTART, data="darkness"),
            dict(text=STRINGS.UI.SANDBOXMENU.CAVESTART, data="caves"),
        ]
    PL.LUA_BUILTINS.update(startlocations=startlocations)
    class tasksets:
        GetGenTaskLists = [
            dict(text=STRINGS.UI.CUSTOMIZATIONSCREEN.TASKSETNAMES.DEFAULT, data="default"),
            dict(text=STRINGS.UI.CUSTOMIZATIONSCREEN.TASKSETNAMES.CLASSIC, data="classic"),
            dict(text=STRINGS.UI.CUSTOMIZATIONSCREEN.TASKSETNAMES.CAVE_DEFAULT, data="cave_default"),
        ]
    PL.LUA_BUILTINS.update(tasksets=tasksets)
    lp = PL.LUAParser(global_=PL.LUA_BUILTINS)
    with zipfile.ZipFile(SCRIPT_FILE) as zip:
        content = zip.read("scripts/map/customize.lua")
    fp = io.StringIO(content.decode("utf8"))
    lp.parse_lua(lua_file=fp, start_line=5, end_cond=_end_read_settings)
    result = PL.LuaDict()
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


def read_worldgen_override(cluster="Master"):
    path = os.path.join(CLUSTER_DIR, cluster, "worldgenoverride.lua")
    if os.path.exists(path):
        with open(path, 'r') as fp:
            lp = PL.LUAParser(global_=PL.LUA_BUILTINS)
            content_ = fp.read()
            idx = content_.find("return")
            prefix = content_[:idx]
            content = content_[idx:]
            lp.parse_lua_line(content)
        override = lp.global_['__rt']
        return override
    else:
        return None


def fetch_item_settings(item):
    # for certain item, list all valid settings
    # then return possible items in a dictionary
    if is_translated(item):
        _item = get_closest_item(item)
        if type(_item) is str:
            items = [_item]
        else:
            items = _item
    else:
        items = [item]
    settings = read_level_settings()
    result = {}
    for i in items:
        for k, v in settings.items():
            if i in v:  # misc
                result[i] = []
            elif type(v) is PL.LuaDict:
                for cate, detail in v.items():
                    if i in detail['items']:
                        desc = detail['items'][i].get("desc", detail['desc'])
                        result[i] = [d['data'] for d in desc]
    return result


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
        elif len(valid_values) > 1:
            return False, \
                f"multi item name: {list(valid_values.keys())} match {item}"
        else:
            valid_values = tuple(valid_values.values())[0]
        if value in valid_values:
            override['overrides'][item] = value
            PL.LUA_dump(override)
            path = os.path.join(CLUSTER_DIR, cluster, "leveldataoverride.lua")
            write_to_override(override, path)
            return True, None
        else:
            return False, f'{value} not in: {valid_values}'
    else:
        return False, 'level data override file path not exists'


def rewrite_worldgen_item(item, value, cluster="Master"):
    override = read_worldgen_override(cluster=cluster)
    if override:
        valid_values = fetch_item_settings(item)
        if valid_values is None:
            return False, f'No such item:{item}'
        elif len(valid_values) > 1:
            return False, \
                f"multi item name: {list(valid_values.keys())} match {item}"
        else:
            valid_values = tuple(valid_values.values())[0]
        if value in valid_values:
            if not issubclass(type(override['overrides']), dict):
                override['overrides'] = PL.LuaDict()
            override['overrides'][item] = value
            PL.LUA_dump(override)
            path = os.path.join(CLUSTER_DIR, cluster, "worldgenoverride.lua")
            write_to_override(override, path, prepend="KLEI     1 ")
            return True, None
        else:
            return False, f'{value} not in: {valid_values}'
    else:
        return False, 'worldgen override file path not exists'


def write_to_override(override, path, prepend=""):
    or_ = PL.LUA_dump(override)
    with open(path, 'w') as fp:
        fp.write(prepend)
        fp.write("return ")
        fp.write(or_)


# if __name__ == "__main__":
#     OR = read_worldgen_override()
#     LS = read_level_settings()
#     import pprint
#     pprint.pprint(LS, indent=2)
#     pp = pprint.PrettyPrinter()
#     with open("level_settings.txt", 'w') as fp:
#         fp.write(pp.pformat(LS))
#     print(OR)
#     print(fetch_item_settings('草草'))

def puralize(obj):
    print(type(obj))
    if type(obj) == PL.LuaDict:
        r = {}
        for k, v in obj.items():
            if type(v) in (PL.LuaDict, PL.LuaList, PL.LazyText):
                r[k] = puralize(v)
            else:
                r[k] = v
    elif type(obj) == PL.LuaList:
        r = []
        for v in obj:
            if type(v) in (PL.LuaDict, PL.LuaList, PL.LazyText):
                r.append(puralize(v))
            else:
                r.append(v)
    elif isinstance(obj, PL.LazyText):
        r = obj.msgstr
    else:
        r = obj
    return r

if __name__ == "__main__":
    ls = read_level_settings()
    ls_pural = puralize(ls)
    with open('level_settings.json', 'w') as fp:
        json.dump(ls_pural, fp, indent=2, ensure_ascii=False)