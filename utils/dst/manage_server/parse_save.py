import os
import sys
import pprint

cwd = os.path.dirname(__file__)
sys.path.append(cwd)
from get_config import CLUSTER_DIR
from mega_backup import HEX_STR
import parse_lua


MAP_ENTS = (
    (  
    # level 1 important
    'hermit_crab',
    'antlion_spawner',
    'resurrectionstone',
    'oasislake',
    'beequeenhive',
    'crabking_spawner',
    'crabking',
    'monkeyisland_portal',
    'dragonfly_spawner',
    'pigking',
    'moonbase',
    'hermithouse_construction1',
    'hermithouse_construction2',
    'hermithouse_construction3',
    'walrus_camp',
    'monkeyqueen',
    'multiplayer_portal',
    'multiplayer_portal_moonrock',
    'wormhole',
    'cave_entrance',
    'cave_entrance_open',
    "moon_altar_rock_glass",
    "moon_altar_rock_seed",
    "moon_altar_rock_idol",
    "moon_altar_astral_marker_1",
    "moon_altar_astral_marker_2",
    'oceanfish_shoalspawner',
    'townportal',
    'moose',
    'mooseegg',
    'deerclop',
    'bearger',
    'charlie_stage_post',
    'statueharp_hedgespawner',
    # Caves
    # "ancient_altar_broken_ruinsrespawner_inst",
    # "ruins_statue_mage_nogem_ruinsrespawner_inst",
    # "ruins_statue_mage_ruinsrespawner_inst",
    # "pillar_atrium",
    # "pillar_ruins",
    "ancient_altar",
    "ancient_altar_broken",
    "ancient_statue",
    # "atrium_rubble",
    # "atrium_statue_facing",
    # "ruins_cavein_obstacle",
    "atrium_key",
    "atrium_gate",
    # "atrium_statue",
    # "spawnpoint_multiplayer", same as cave_exit
    "archive_portal",
    "archive_switch_base",
    # "archive_orchestrina_main",
    # "archive_switch",
    # "archive_orchestrina_small",
    # "archive_security_waypoint",
    # "archive_chandelier",
    "archive_cookpot",
    # "ancient_altar_ruinsrespawner_inst",
    # "archive_ambient_sfx",
    "firepit",
    "minotaurchest",
    # "insanityrock",
    # "sanityrock",
    "hutch",
    "archive_lockbox_dispencer",
    # "spawnpoint_master", same as portal
    "minotaur_ruinsrespawner_inst",
    "cave_exit",
    "toadstool_cap",
    "tentacle_pillar",
    ),
    (  
    # level 2 normal
    # structures
    'birdcage',
    # 'mermhouse_crafted',
    'seafaring_prototyper',
    'tent',
    'researchlab1',
    'researchlab2',
    'researchlab3',
    'researchlab4',
    'firepit',
    ),
)


def parse(save_file, ents_level=0, extra_ents={}, jump_keys={}):
    wanted_ents = set()
    for ents in MAP_ENTS[:ents_level]:
        wanted_ents = wanted_ents.union(ents)
    wanted_ents = wanted_ents.union(extra_ents)
    lp = parse_lua.LUAParser(global_=parse_lua.LUA_BUILTINS)
    fn_name = ""
    savedata = {}
    jump = False
    for line in save_file:
        line = line.strip()
        if line.startswith("local") or line.startswith("end"):
            continue
        elif line.startswith("tablefunctions"):
            fn_name = line.split('"')[1]
            if fn_name in jump_keys:
                    jump = True
            elif fn_name.startswith('ents'):
                if fn_name[5:-3] not in wanted_ents:
                    jump = True
        elif line.startswith("return"):
            if line[6:].strip().startswith("savedata"):
                break
            if jump:
                obj = []
                jump = False
                continue
            content = line[6:]
            # if len(content) > 16000:
            #     obj = {"obj": fn_name}
            # else:
            obj = lp.explain(content)
        elif line.startswith("savedata"):
            l, r = line.split("=", maxsplit=1)
            if "tablefunctions" not in r:
                # special cond for "savedata = {}"
                continue
            parts = l.split('"')
            keys = []
            for i, part in enumerate(parts):
                if i%2 == 1:
                    keys.append(part)
            data = savedata
            if len(keys) > 1:
                for k in keys[:-1]:
                    if k in data:
                        data = data[k]
                    else:
                        data[k] = {}
                        data = data[k]
            data[keys[-1]] = obj
    return savedata


def parse_user(save_file):
    with open(save_file, 'rb') as fp:
        # print(f"parse user in file {save_file}")
        bline = fp.readline()
        line = bline.decode(encoding='utf8', errors='ignore')
    lp = parse_lua.LUAParser(global_=parse_lua.LUA_BUILTINS)
    idx = line.find('return')
    if idx == -1:
        return {}
    s = parse_lua.fetch_end(line[idx+7:])
    userdata = lp.parse_a_table(s)
    # sf = pprint.pformat(userdata, indent=2)
    # fname = os.path.join(cwd, 'temp', 'u_'+save_file.split('/')[-2])
    # with open(fname, 'w') as fp:
    #     fp.write(sf)
    return userdata


def _merge_item_into_items(item, items):
    if item:
            prefab = item['prefab']
            qtty = item.get('data', {}).get('stackable', {}).get('stack', 1)
            qtty_origin = items.setdefault(prefab, 0)
            items[prefab] = qtty_origin + qtty
            data = item.get('data', {})
            cts = data.get('container', {}).get('items', []) or \
                data.get('unwrappable', {}).get('items', [])
            if cts:
                for content in cts:
                    _merge_item_into_items(content, items)


def fetch_user_items(userdata):
    inventory = userdata.get('data', {}).get('inventory', {}).get('items', {})
    items = {}
    for item in inventory:
        _merge_item_into_items(item, items)
    equip = userdata.get('data', {}).get('inventory', {}).get('equip', {}) or {}
    for item in equip.values():
        _merge_item_into_items(item, items)
    return items


def parse_nodes(nodes_str):
    lp = parse_lua.LUAParser(global_=parse_lua.LUA_BUILTINS)
    nodes = lp.explain(nodes_str)
    return nodes


def parse_roads(roads_str):
    lp = parse_lua.LUAParser(global_=parse_lua.LUA_BUILTINS)
    roads = lp.explain(roads_str)
    return roads


def main():
    with open(os.path.join(cwd, 'temp/00002_wierd'), 'r') as fp:
        savedata = parse(fp, ents_level=1)
    print(list(savedata.keys()))
    print(savedata['meta'])
    print(len(savedata['ents']))
    xs = set()
    zs = set()
    for ents in savedata['ents'].values():
        for ent in ents:
            try:
                x = ent.get('x')
                z = ent.get('z')
            except KeyError:
                print(f"no coord {ent}")
                continue
            else:
                xs.add(x)
                zs.add(z)
    print("max x:", max(xs), "min x:", min(xs))
    print("max z:", max(zs), "min z:", min(zs))
    from draw_map import draw_ents, draw_background, draw_nodes, draw_roads, \
        draw_tiles
    im = None
    tiles = parse_map_nav(savedata['map']['tiles'])
    height = savedata['map']['height']
    width = savedata['map']['width']
    im = draw_tiles(tiles, width=width, height=height)
    # with open(os.path.join(cwd, "temp/nodes.lua"), 'r') as fp:
    #     s = fp.read()
    # n = parse_nodes(s)
    # im = draw_nodes(n, im=im)
    # with open(os.path.join(cwd, "temp/roads.lua"), 'r') as fp:
    #     s = fp.read()
    # r = parse_roads(s)
    # im = draw_roads(r, im=im)
    im = draw_ents(savedata, im=im)
    im.show()


def base64_to_int(ch):
    # char to int
    if ord(ch) >= ord('A') and ord(ch) <= ord('Z'):
        return ord(ch) - ord('A')
    elif ord(ch) >= ord('a') and ord(ch) <= ord("z"):
        return ord(ch) - ord('a') + 26
    elif ch.isdigit():
        return int(ch) + 52
    elif ch == '+':
        return 62
    elif ch == '/':
        return 63
    else:
        raise ValueError(f'char:{ch} invalid for trans from base64')


def base64s_to_bin_str(chs):
    # chars to bin str : 'ABCD' -> '000000000001000010000011'
    result = ""
    for ch in chs:
        if ch != "=":
            result += "{:06b}".format(base64_to_int(ch))
        else:
            result += "00"
    return result


def parse_map_nav(nav):
    chs = nav[12:]
    bs = base64s_to_bin_str(chs)
    tiles = []
    while bs:
        tile_str = bs[:16]
        if len(tile_str) < 16:
            print(f"parse rest: {len(tile_str)}")
            break
        tile = tile_str[8:] + tile_str[:8]
        tile_id = int(tile, base=2)
        tiles.append(tile_id)
        bs = bs[16:]
    return tiles


def merge_ents(*ents_list):
    ents_dict = {}
    for ents in ents_list:
        for k, v in ents.items():
            if k in ents_dict:
                ents_dict[k] = ents_dict[k] + v
            else:
                ents_dict[k] = v
    return ents_dict


def get_latest_save(user=False, cluster=CLUSTER_DIR):
    save = {}
    if user:
        u = {}
        save['user'] = {}
    HEX_STR = "0123456789ABCDEF"
    SESSION_STR = "0123456789ABCDEFGHIJKLMNOPQRSTUV"
    is_user_entry = lambda x: x.is_dir() and len(x.name) == 12 and \
            all(map(lambda y: y in SESSION_STR, x.name))
    for level in ('Master', 'Caves'):
        cluster_dir = os.path.join(cluster, level, 'save/session', )
        if os.path.exists(cluster_dir):
            folders = os.listdir(cluster_dir)
            for folder in folders:
                if len(folder) == 16 and \
                        all(map(lambda x: x in HEX_STR, folder)):
                    save_dir = os.path.join(cluster_dir, folder)
                    break
            else:
                save_dir = None
            if save_dir is None:
                print(f"No save dir in {cluster_dir}")
                continue
            latest_entry = _fetch_lastest_save(save_dir)
            save[level] = latest_entry
            if user:
                for u_dir_entry in filter(is_user_entry, os.scandir(save_dir)):
                    u_max_entry = _fetch_lastest_save(u_dir_entry)
                    if u_max_entry is not None:
                        u_max_entries = u.get(u_dir_entry.name, [])
                        u_max_entries.append(u_max_entry)
                        u[u_dir_entry.name] = u_max_entries
        else:
            print(f'No such dir:{cluster_dir}')
    
    if user:
        for user_session, user_etries in u.items():
            if user_etries:
                max_entry = max(user_etries, key=lambda x: x.stat().st_ctime)
                save['user'][user_session] = max_entry
    return save


def _fetch_lastest_save(save_dir):
    try:
        m = max(filter(
            lambda x: x.name.isdigit(), 
            os.scandir(save_dir)
            ), 
            key=lambda x: int(x.name)
        )
    except ValueError:
        # save_dir is empty
        m = None
    # print('fetch :', m.name if m else 'None')
    return m


def countprefab(prefab, cluster_dir):
    """
    :param last_check: timestamp that last check these things
    """
    from get_progress import merge_container, CONTAINERS
    result = {'user':{}}
    save = get_latest_save(user=True, cluster=cluster_dir)
    master_entry = save.get('Master')
    caves_entry = save.get('Caves')
    parsed_map = []
    for p in (master_entry, caves_entry):
        if p:
            with open(p.path, 'r') as fp:
                ents = parse(fp,
                    extra_ents={prefab,}.union(CONTAINERS),
                    jump_keys={'map',},
                )['ents']
                contained_ents = merge_container(ents)
                parsed_map.append(ents)
                parsed_map.append(contained_ents)
    ents_on_map = merge_ents(*parsed_map)  # prefab: [{data},...]
    if prefab in ents_on_map:
        result['map'] = len(ents_on_map[prefab])
    for user_session, entry in save.get('user', {}).items():
        userdata = parse_user(entry.path)
        items = fetch_user_items(userdata)
        if prefab in items:
            result['user'][user_session] = items[prefab]
    return result

if __name__ == "__main__":
    main()

