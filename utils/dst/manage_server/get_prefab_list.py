import os
import sys
import zipfile
import io
import json

cwd = os.path.dirname(__file__)
sys.path.append(cwd)
from get_config import SCRIPT_FILE

LAN_PATH = 'scripts/languages/chinese_s.po'
TRANS_FILE = os.path.join(cwd, "translations.json")

PREFABS = {}

def update():
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
    PREFABS.update(translations)
    with open(TRANS_FILE, 'w') as fp:
        json.dump(translations, fp=fp, indent=2, ensure_ascii=False)


if os.path.exists(TRANS_FILE):
    with open(TRANS_FILE, 'r') as fp:
        PREFABS.update(json.load(fp))

EXTRA_PREFABS = {
    # 'antlion_spawner': '蚁狮',
    # 'dragonfly_spawner': '龙蝇',
    # 'tumbleweedspawner': '风滚草',
    # 'crabking_spawner': '帝王蟹',
    'hermithouse_construction1': '寄居蟹隐士之家',
    'hermithouse_construction2': '寄居蟹隐士之家',
    'hermithouse_construction3': '寄居蟹隐士之家',
    'oceanfish_shoalspawner': '鱼群',
    'moose': '麋鹿鹅',
    'mooseegg': '麋鹿鹅蛋',
}

PREFABS.update(EXTRA_PREFABS)

REVERSE_PREFABS = {}
for k, v in PREFABS.items():
    if v in REVERSE_PREFABS:
        REVERSE_PREFABS[v].append(k)
    else:
        REVERSE_PREFABS[v] = [k,]

if __name__ == "__main__":
    update()
