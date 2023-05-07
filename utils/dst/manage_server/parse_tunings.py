import os
import sys
import io
import zipfile
import math as Math

CWD = os.path.dirname(__file__)
sys.path.append(CWD)
from get_config import SCRIPT_FILE
import parse_lua as PL


def get_tunings():
    with zipfile.ZipFile(SCRIPT_FILE) as zip:
        content = zip.read("scripts/tuning.lua")
    fp = io.StringIO(content.decode("utf8"))
    lp = PL.LUAParser(global_=PL.LUA_BUILTINS)
    lp.global_.update(TechTree=TechTree)
    lp.global_.update(RADIANS=180/3.1415, math=math, FRAMES=1/30)
    lp.parse_lua(fp, start_line=18, end_cond=lambda x: "ORIGINAL_TUNING" in x)
    return lp.global_['TUNING']

class TechTree:
    AVAILABLE_TECH = {
        "SCIENCE",
        "MAGIC",
        "ANCIENT",
        "CELESTIAL",
        "MOON_ALTAR", 
        "SHADOW",
        "CARTOGRAPHY",
        "SEAFARING",
        "SCULPTING",
        "ORPHANAGE", 
        "PERDOFFERING",
        "WARGOFFERING",
        "PIGOFFERING",
        "CARRATOFFERING",
        "BEEFOFFERING",
        "CATCOONOFFERING",
        "MADSCIENCE",
        "CARNIVAL_PRIZESHOP",
        "CARNIVAL_HOSTSHOP",
        "FOODPROCESSING",
        "FISHING",
        "WINTERSFEASTCOOKING",
        "HERMITCRABSHOP",
        "TURFCRAFTING",
        "MASHTURFCRAFTING",
        "SPIDERCRAFT",
        "ROBOTMODULECRAFT",
        "BOOKCRAFT",
    }

    @classmethod
    def Create(cls, t):
        t = t or {}
        for i, v in enumerate(cls.AVAILABLE_TECH):
            t[v] = t.get(v) or 0
        return t

class math:
    pi = Math.pi
    huge = Math.inf

    @classmethod
    def pow(cls, *args):
        return pow(*args)
    
    @classmethod
    def ceil(cls, *args):
        return Math.ceil(*args)
    
    @classmethod
    def floor(cls, *args):
        return Math.floor(*args)
    

if __name__ == "__main__":
    res = get_tunings()
    with open("tunings.txt", 'w') as fp:
        fp.write(repr(res))
