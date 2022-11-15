import re

FIND_A_PLAYER_PATTERN = re.compile("""UserToPlayer\('(?P<ku>[\w_-]+)""")

PTNS = dict(
    c_spawn_pattern = {'pattern': re.compile("""SpawnPrefab\("(?P<prefab>[^"]+)", "(?P<skinname>[^"]+)", (?P<quantity>[^,]+), "(?P<ku>[\w_-]+)"\)"""), 'has_player': True},
    c_create_pattern = {'pattern': re.compile("GiveAllRecipes"), 'has_player': True},
    reveal_map_pattern = {'pattern': re.compile("player_classified.MapExplorer"), 'has_player': True},
    teleport_pattern = {'pattern': re.compile("Transform:SetPosition"), 'has_player': True},
    clear_backpack_pattern = {'pattern': re.compile("backpackSlotCount"), 'has_player': True},
    clear_inventory_pattern = {'pattern': re.compile("inventorySlotCount"), 'has_player': True},
    one_hit_kill_pattern = {'pattern': re.compile("c\.CalcDamage"), 'has_player': True},
    remove_pattern = {'pattern': re.compile("components.firefx:Extinguish.+obj:Remove"), 'has_player': True},
    extinguish_pattern = {'pattern': re.compile("components.firefx:Extinguish"), 'has_player': True},
    goto_pattern = {'pattern': re.compile("local function tmi_goto(prefab)"), 'has_player': True},
    health_pattern = {'pattern': re.compile("player.components.health"), 'has_player': True},
    sanity_pattern = {'pattern':re.compile("player.components.sanity"), 'has_player':True},
    hunger_pattern = {'pattern': re.compile("player.components.hunger"), 'has_player': True},
    moisture_pattern = {'pattern': re.compile("player.components.moisture"), 'has_player': True},
    temprature_pattern = {'pattern': re.compile("player.components.temprature"), 'has_player': True},
    speed_pattern = {'pattern': re.compile("components.locomotor:SetExternalSpeedMultiplier"), 'has_player': True},
    skip_pattern = {'pattern': re.compile("c_skip")},
    time_scale_pattern = {'pattern': re.compile("TheSim:SetTimeScale")},
    lightningstrike_pattern = {'pattern': re.compile('TheWorld:PushEvent\("ms_sendlightningstrike"'), 'has_player': True},
    raining_pattern = {'pattern': re.compile('TheWorld:PushEvent\("ms_forceprecipitation"')},
    get_domestic_beefalo_pattern = {'pattern': re.compile("components.domesticatable:DeltaTendency"), 'has_player': True},
)