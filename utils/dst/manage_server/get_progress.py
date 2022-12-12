from bdb import checkfuncname
import os
import sys

cwd = os.path.dirname(__file__)
sys.path.append(cwd)
from parse_save import parse, merge_ents, get_latest_save
from parse_lua import LuaDict, LuaList

ENTS = {
    # CELESTIAL CHAMPION LINE
    # all inserted moon altar
    'moon_altar',
    'moon_altar_astral',
    'moon_altar_cosmic',
    # moon altar parts
    'moon_altar_glass',
    'moon_altar_seed',
    'moon_altar_idol',
    # moon altar astral parts
    'moon_altra_icon', 
    'moon_altra_ward', 
    # moon altar cosmic parts
    'moon_altar_crown',
    # unworked moon altar parts
    'moon_altar_rock_glass',
    'moon_altar_rock_seed',
    'moon_altar_rock_idol',
    # underground moon altar astral
    'moon_altar_astral_marker_1',
    'moon_altar_astral_marker_2',
    # archive resonator to be used
    'archive_resonator_item',
    'archive_resonator',
    # archive switch
    'archive_switch',
    # unused pearl
    'hermit_pearl'
    # hermit crab's tasks to be done 
    'hermit_crab',
    
    # SHADOWWEAVER LINE
    # shadow heart line
    'shadowheart',
    # chess piece
    'chesspiece_rook_marble',
    'chesspiece_knight_marble',
    'chesspiece_bisop_marble',
    'chesspiece_rook_stone',
    'chesspiece_knight_stone',
    'chesspiece_bisop_stone',
    # sketch in sculptingtable
    'sculptingtable',
    # sketches 
    'sketch',
    # suspicious marble
    'sculpture_rooknose',
    'sculpture_knighthead',
    'sculpture_bishophead',
    'sculpture_rookbody',
    'sculpture_bishopbody',
    'sculpture_knightbody',
    # fossils line
    'fossil_piece',
    'fossil_stalker',
    # atrium key line
    'atrium_key',
    'ancient_guardian',
}

CONTAINERS = {
    'hutch',
    'icebox',
    'cookpot',
    'archive_cookpot',
    'minotaurchest',
    'backpack',
    'treasurechest',
    'sacred_chest',
    'seedpouch',
    "dragonflychest",
    'mushroom_light2',
    'portablecookpot',
    "sisturn",
    "bookstation",
    'ocean_trawler',
    "portablespicer",
    'fish_box',
    "icepack",
    "chester",
    "terrariumchest",
    "saltbox",
    "shadow_container",
    "supertacklecontainer",
    # temp unwanted
    # 'pandoraschest',
    # "underwater_salvageable",


    # MOD medal things 
    "medal_resonator_item",
    "medal_cookpot",
    "medal_livingroot_chest",
    "spices_box",
    "multivariate_certificate",
    "large_multivariate_certificate",
    "medal_spacetime_chest",
    "medal_krampus_chest_item",
    "medal_ammo_box",

    # MOD legion things
    "backcub",
    "hiddenmoonlight",
    "revolvedmoonlight_pro",
    "revolvedmoonlight_item",
    "boltwingout",
}


HERMIT_TASKS = (
    'FIX_HOUSE_1',
    'FIX_HOUSE_2',
    'FIX_HOUSE_3',
    'PLANT_FLOWERS',
    'REMOVE_JUNK',
    'PLANT_BERRIES',
    'FILL_MEATRACKS',
    'GIVE_HEAVY_FISH',
    'REMOVE_LUREPLANT',
    'GIVE_UMBRELLA',
    'GIVE_PUFFY_VEST',
    'GIVE_FLOWER_SALAD',
    None,
    'GIVE_BIG_WINTER',
    'GIVE_BIG_SUMMER',
    'GIVE_BIG_SPRING',
    'GIVE_BIG_AUTUM',
)


def merge_container(ents):
    # merge all containers and return an ents-like dict
    content_data = LuaDict()
    for container_name in CONTAINERS:
        if container_name in ents:
            containers = ents[container_name]
            for container in containers:
                try:
                    items = container['data']['container']['items']
                except KeyError as e:
                    print(f"unfound key in container {container_name}"
                        f": {container} ERROR: {e}")
                    continue
                for item in items:
                    if item is None:
                        continue
                    prefab = item['prefab']
                    if prefab not in content_data:
                        content_data[prefab] = LuaList()
                    content_data[prefab].append(item)
    return content_data


def get_progress_celestial_line(ents):
    # inserted
    exists = lambda x: x in ents
    def check_archive_switch(prefab):
        objs = ents[prefab]
        remainder = 0
        for obj in objs:
            data = obj.get('data', {})
            if data.get('spawnopal') or data.get('pickable', {}).get('picked'):
                remainder += 1
        if remainder == 3:
            return True
        else:
            return remainder
    def check_hermit_crab(prefab):
        objs = ents.get(prefab)
        if objs is None:
            return "NOT MEET"
        obj = objs[0]
        data = obj['data']
        if data.get('pearlgiven'):
            return True
        else:
            taskscomplete = data['friendlevel'].get('taskscomplete', ())
            tasks_done = filter(lambda x: 
                HERMIT_TASKS.index(x) < len(taskscomplete)
                and (x and taskscomplete[HERMIT_TASKS.index(x)])
            )
            return " ".join(tasks_done)
    line_altar = (
        ('moon_altar', exists, (
            ('moon_altar_glass', exists, (
                ('moon_altar_rock_glass', exists),
            )),
            ('moon_altar_seed', exists, (
                ('moon_altar_rock_glass', exists),
            )),
            ('moon_altar_idol', exists, (
                ('moon_altar_rock_idol', exists),
            )),
        )), 
    )

    _astral_subpart = ('archive_resonator_item', 'archive_resonator', exists, (
                        ('archive_switch', check_archive_switch),
    ))
    line_altar_astral = (
        ('moon_altar_astral', exists, (
            ('moon_altar_icon', exists, (
                ('moon_altar_astral_marker_1', exists),
                    _astral_subpart,
                ),
            ),
            ('moon_altar_ward', exists, (
                ('moon_altar_astral_marker_2', exists),
                _astral_subpart,
                ),
            )),
        ),
    )
    
    line_altar_cosmic = (
        ('moon_altar_cosmic', exists, (
            ('hermit_pearl', exists, (
                ('hermit_crab', check_hermit_crab),
            )),
        )),
    )
    return (get_line_process(line_altar),
        get_line_process(line_altar_astral),
        get_line_process(line_altar_cosmic))

TRUE_STR = " 已满足"
FALSE_STR = " 未满足"
def get_line_process(line, top=False):
    line_results = []
    for task in line:
        results = []
        for ele in task:
            if callable(ele):
                check_fn = ele
                break
        idx = task.index(check_fn)
        for to_check in task[:idx]:
            result = (to_check, check_fn(to_check))
            results.append(result)
        if any(filter(lambda x: x[1] is True, results)) or len(task) == idx+1:
            pass
        else:
            results = get_line_process(task[idx+1])
        line_results.append(results)
    return line_results

def main():
    saves = get_latest_save()
    save_file_master = saves['Master']
    save_file_cave = saves['Caves']
    with open(save_file_master, 'r') as fp:
        savedata = parse(fp, extra_ents=ENTS.union(CONTAINERS))
    content_data = merge_container(savedata['ents'])
    ents1 = merge_ents(content_data, 
        {k: v for k, v in savedata['ents'].items() if v})
    with open(save_file_cave, 'r') as fp:
        savedata = parse(fp, extra_ents=ENTS.union(CONTAINERS))
    content_data = merge_container(savedata['ents'])
    ents2 = merge_ents(content_data, 
        {k: v for k, v in savedata['ents'].items() if v})
    ents = merge_ents(ents1, ents2)
    result = get_progress_celestial_line(ents)
    print(result)


if __name__ == '__main__':
    main()