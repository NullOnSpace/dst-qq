import os
import sys
import zipfile
import io
import json
import redis

cwd = os.path.dirname(__file__)
sys.path.append(cwd)
from get_config import SCRIPT_FILE

LAN_PATH = 'scripts/languages/chinese_s.po'
TRANS_FILE = os.path.join(cwd, "translations.json")

REDIS_PREFABS = 'dst:data:prefabs'

PREFABS = {}

def update():
    r = redis.Redis(decode_responses=True)
    _CACHED_PREFABS = r.hgetall(REDIS_PREFABS)
    for k, v in _CACHED_PREFABS.items():
        PREFABS[k.lower()] = v
    with open(TRANS_FILE, 'w') as fp:
        json.dump(PREFABS, fp=fp, indent=2, ensure_ascii=False)
    r.close()

def get_prefabs_from_source():
    with zipfile.ZipFile(SCRIPT_FILE) as zip:
        content = zip.read(LAN_PATH)
    fp = io.StringIO(content.decode("utf8"))
    del content
    start = False
    translations = {}
    prefab = None
    for line in filter(lambda x: not x.startswith("#") and x.strip(), fp):
        if start is False and \
                (not line.startswith("msgc") or "STRINGS.NAMES" not in line):
            continue
        else:
            start = True
            if line.startswith("msgc"):
                prefab = line.split(".")[-1].strip().strip('"').lower()
            elif line.startswith("msgstr"):
                translation = line.strip().split(" ")[-1].strip('"')
                translations[prefab] = translation
                prefab = None
            else:
                continue
        if start and line.startswith("msgc") and "STRINGS.NAMES" not in line:
            break
    return translations

update()

EXTRA_PREFABS = {
    'antlion_spawner': '蚁狮刷新点',
    'dragonfly_spawner': '龙蝇刷新点',
    'tumbleweedspawner': '风滚草刷新点',
    'crabking_spawner': '帝王蟹刷新点',
    'hermithouse_construction1': '寄居蟹隐士之家1',
    'hermithouse_construction2': '寄居蟹隐士之家2',
    'hermithouse_construction3': '寄居蟹隐士之家3',
    'oceanfish_shoalspawner': '鱼群刷新点',
    'moose': '麋鹿鹅',
    'mooseegg': '麋鹿鹅蛋',
}

PREFABS.update(EXTRA_PREFABS)


def get_reverse_prefabs():
    reverse_prefabs = {}
    for k, v in PREFABS.items():
        if v in reverse_prefabs:
            reverse_prefabs[v].append(k)
        else:
            reverse_prefabs[v] = [k,]
    return reverse_prefabs

REVERSE_PREFABS = get_reverse_prefabs()

def get_prefabs_with_duplicate_names():
    from pypinyin import pinyin, Style
    for k in sorted(REVERSE_PREFABS.keys(), 
            key=lambda x: [pinyin(x[0], style=Style.TONE3)]):
        v = REVERSE_PREFABS[k]
        if len(v) > 1:
            print(k , v)


if __name__ == "__main__":
    get_prefabs_with_duplicate_names()