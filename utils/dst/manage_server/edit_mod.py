import re
import os

from parse_lua import LUAParser, LUA_BUILTINS
from get_config import CLUSTER_DIR, INSTALL_DIR

"""
parse settings like setting={
    \d+={},
    ...
}

"""

SAMPLE = """
configuration_options = {
    {
        name = "SHOWBADGES",
        label = "Show Temp Icons",
        hover = "Show images that indicate",
        options =	{
            {description = "Show", data = true, hover = "Badges will only be shown"},
            {description = "Hide", data = false, hover = "Badges will never be shown."},
        },
        default = true,
    },
    {
		name = "UNIT",
		label = "Temperature Unit",
		hover = "Do the right thing",
		options =	{
						{description = "Units", data = "T",
							hover = "The temperature numbers Freeze at 0"},
						{description = "Celsius", data = "C",
							hover = "The temperature numbers get warned 2.5 from each."},
						{description = "Fahrenheit", data = "F",
							hover = "Your favorite temperature get warned 9 from each."},
					},
		default = "T",
	}
}
"""

pattern_setting = r"=\s+\{\s+\}"
pattern_config = re.compile(
    "configration_options\s*=\s*\{\}"
)

MOD_SETTING_FILE = os.path.join(CLUSTER_DIR, 'Master/modoverrides.lua')
MOD_UPDATE_FILE = os.path.join(INSTALL_DIR, 'mods/dedicated_server_mods_setup.lua')

def parse_mod(mod_setting_file):
    with open(mod_setting_file, 'r') as fp:
        content = fp.read()
    lp = LUAParser(global_=LUA_BUILTINS)
    lp.parse_lua_line(content)
    rt = lp.global_['__rt']
    return rt


def add_mod_auto_update(mods):
    cached_mods_setup = set()
    cached_mods_collection = set()
    MOD_SETUP_TPL = 'ServerModSetup("{mod_id}")\n'
    MOD_COLLECTION_TPL = 'ServerModCollectionSetup("{mod_id}")\n'
    with open(MOD_UPDATE_FILE, 'r') as fp:
        for line in fp:
            stripped_line = line.strip()
            if stripped_line.startswith("ServerModSetup"):
                mod_id = stripped_line[16:].rstrip('")')
                cached_mods_setup.add(mod_id)
            elif stripped_line.startswith("ServerModCollectionSetup"):
                mod_id = stripped_line[26:].rstrip('")')
                cached_mods_collection.add(mod_id)
    with open(MOD_UPDATE_FILE, 'a') as fp:
        fp.write("\n")
        for mod_id in mods:
            if not str(mod_id) in cached_mods_setup:
                fp.write(MOD_SETUP_TPL.format(mod_id=mod_id))
            if not str(mod_id) in cached_mods_collection:
                fp.write(MOD_COLLECTION_TPL.format(mod_id=mod_id))


def add_server_mod_to_auto_update():
    mod_sts = parse_mod(MOD_SETTING_FILE)
    mod_ids = map(lambda x: x[9:], mod_sts)
    add_mod_auto_update(mod_ids)

if __name__ == "__main__":
    add_server_mod_to_auto_update()