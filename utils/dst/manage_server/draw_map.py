from PIL import Image, ImageDraw, ImageFont

import os
import sys

cwd = os.path.dirname(__file__)
sys.path.append(cwd)

from get_prefab_list import PREFABS as ENT_TRANSLATION

HEIGHT = WIDTH = 439*4


fnt_imp = ImageFont.truetype(
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", size=30)
fnt_info = ImageFont.truetype(
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", size=24)
fnt_debug = ImageFont.truetype("Pillow/Tests/fonts/FreeMono.ttf", size=12)


TILE_ID_MAP = dict(
    OCEAN_COASTAL=201,
    WALL_HUNESTONE=160,
    UNDERGROUND=128,
    METEORMINE_NOISE=121,
    ROAD=2,
    QUAGMIRE_SOIL=39,
    MUD=17,
    OCEAN_HAZARDOUS=207,
    OCEAN_WATERLOG=208,
    SHELLBEACH=44,
    OCEAN_BRINEPOOL_SHORE=206,
    TRIM=22,
    WALL_STONEEYE_GLOW=163,
    METEOR=43,
    WALL_ROCKY=151,
    FUNGUSMOON=46,
    PEBBLEBEACH=42,
    SCALE=32,
    OCEAN_COASTAL_SHORE=202,
    FAKE_GROUND=200,
    LAVAARENA_FLOOR=33,
    WALL_DIRT=152,
    LAVAARENA_TRIM=34,
    TILES_GLOW=21,
    OCEAN_END=247,
    GROUND_NOISE=125,
    MARSH=8,
    QUAGMIRE_PEATFOREST=35,
    WALL_TOP=158,
    WALL_MARSH=153,
    FUNGUSRED=24,
    FUNGUS_NOISE=127,
    METEORCOAST_NOISE=122,
    BRICK_GLOW=19,
    WEB=9,
    WOODFLOOR=10,
    TILES=20,
    OCEAN_BRINEPOOL=205,
    FUNGUS=14,
    ABYSS_NOISE=124,
    IMPASSABLE=1,
    FARMING_SOIL=47,
    UNDERROCK=16,
    SAVANNA=5,
    WALL_CAVE=154,
    WALL_MUD=157,
    DIRT=4,
    WALL_FUNGUS=155,
    WALL_WOOD=159,
    QUAGMIRE_CITYSTONE=41,
    WALL_SINKHOLE=156,
    WALL_HUNESTONE_GLOW=161,
    MONKEY_DOCK=257,
    OCEAN_ROUGH=204,
    ROCKY=3,
    CARPET=11,
    OCEAN_SWELL=203,
    QUAGMIRE_PARKFIELD=36,
    INVALID=65535,
    DESERT_DIRT=31,
    MONKEY_GROUND=256,
    GRASS=6,
    CAVE_NOISE=126,
    CAVE=13,
    FUNGUSMOON_NOISE=120,
    DIRT_NOISE=123,
    FOREST=7,
    SINKHOLE=15,
    QUAGMIRE_GATEWAY=38,
    WALL_STONEEYE=162,
    TRIM_GLOW=23,
    FUNGUSGREEN=25,
    BRICK=18,
    QUAGMIRE_PARKSTONE=37,
    DECIDUOUS=30,
    ARCHIVE=45,
    CHECKER=12
)

TILE_ID_REVERSE_MAP = {v: k for k, v in TILE_ID_MAP.items()}

TILE_COLOR_MAP = dict(
    OCEAN_COASTAL='#70f3ff',
    WALL_HUNESTONE=160,
    UNDERGROUND=128,
    METEORMINE_NOISE=121,
    ROAD='#75878a',
    QUAGMIRE_SOIL=39,
    MUD='#493131',
    OCEAN_HAZARDOUS='#4b5cc4',
    OCEAN_WATERLOG='#a1afc9',
    SHELLBEACH='#75878a',
    OCEAN_BRINEPOOL_SHORE='#177cb0',
    TRIM=22,
    WALL_STONEEYE_GLOW=163,
    METEOR='#7397ab',
    WALL_ROCKY=151,
    FUNGUSMOON=46,
    PEBBLEBEACH='#d1d9e0',
    SCALE='#622a1d',
    OCEAN_COASTAL_SHORE='#3b2e7e',
    FAKE_GROUND=200,
    LAVAARENA_FLOOR=33,
    WALL_DIRT=152,
    LAVAARENA_TRIM=34,
    TILES_GLOW=21,
    OCEAN_END=247,
    GROUND_NOISE=125,
    MARSH='#56004f',
    QUAGMIRE_PEATFOREST=35,
    WALL_TOP=158,
    WALL_MARSH=153,
    FUNGUSRED=24,
    FUNGUS_NOISE=127,
    METEORCOAST_NOISE=122,
    BRICK_GLOW=19,
    WEB=9,
    WOODFLOOR='#789262',
    TILES=20,
    OCEAN_BRINEPOOL='#44cef6',
    FUNGUS=14,
    ABYSS_NOISE=124,
    IMPASSABLE='#161823',
    FARMING_SOIL='#424c50',
    UNDERROCK=16,
    SAVANNA='#eaff56',
    WALL_CAVE=154,
    WALL_MUD=157,
    DIRT='#3d3b4f',
    WALL_FUNGUS=155,
    WALL_WOOD=159,
    QUAGMIRE_CITYSTONE=41,
    WALL_SINKHOLE=156,
    WALL_HUNESTONE_GLOW=161,
    MONKEY_DOCK='#827100',
    OCEAN_ROUGH='#065279',
    ROCKY='#808080',
    CARPET='#801dae',
    OCEAN_SWELL='#801dae',
    QUAGMIRE_PARKFIELD=36,
    INVALID=65535,
    DESERT_DIRT='#c89b40',
    MONKEY_GROUND='#d9b611',
    GRASS='#0c8918',
    CAVE_NOISE=126,
    CAVE=13,
    FUNGUSMOON_NOISE=120,
    DIRT_NOISE=123,
    FOREST='#424c50',
    SINKHOLE=15,
    QUAGMIRE_GATEWAY=38,
    WALL_STONEEYE=162,
    TRIM_GLOW=23,
    FUNGUSGREEN=25,
    BRICK=18,
    QUAGMIRE_PARKSTONE=37,
    DECIDUOUS='#ff8936',
    ARCHIVE=45,
    CHECKER='#f0f0f4',
)


def draw_ents(savedata, im=None):
    if im is None:
        im = Image.new("RGB", (WIDTH, HEIGHT), color="#FEFEFE")
    draw = ImageDraw.Draw(im)
    ents = savedata["ents"]
    for prefab, details in ents.items():
        if prefab in ("wormhole", "tentacle_pillar", "tentacle_pillar_hole"):
            _draw_wormholes(details, im, prefab)
            continue
        for detail in details:
            ent_name = ENT_TRANSLATION.get(prefab, prefab)
            x = detail.get("x")
            z = detail.get("z")
            crd = coord2((x, z))
            draw.rectangle(
                [(crd[0]-1, crd[1]+1), (crd[0]+1, crd[1]-1)], 
                outline="#010101")
            draw.text(crd, ent_name, fill="#010101", anchor="md", font=fnt_imp)
            # draw.text(crd, 
            #         str((x, z)), fill="#010101", anchor="ma", font=fnt_debug)
    return im


def _draw_wormholes(worms, im, prefab):
    draw = ImageDraw.Draw(im)
    colors = [
        "#BDDD22",
        "#44CEF6",
        "#f00056",
        "#eaff56",
        "#549688",
        "#eacd76",
    ]
    bid = {}
    for worm in worms:
        id_ = worm["id"]
        x = worm["x"]
        z = worm["z"]
        crd = coord2((x, z))
        if id_ in bid:
            color, serial = bid[id_]
        else:
            color = colors.pop()
            target = worm['data']['teleporter'].get('target')
            if target is not None:
                serial = len(bid)
                bid[target] = (color, serial)
            else:
                serial = ""
        draw.rectangle(
                [(crd[0]-3, crd[1]+3), (crd[0]+3, crd[1]-3)], 
                outline=color, fill=color)
        name = ENT_TRANSLATION.get(prefab, prefab)
        draw.text(crd, name+str(serial), 
                fill="#010101", anchor="md", font=fnt_info)


def draw_background(map_file, im=None):
    if im is None:
        im = Image.new("RGB", (WIDTH, HEIGHT), color="#FEFEFE")
    draw = ImageDraw.Draw(im)
    with open(map_file, 'r') as fp:
        fp.read(6)
        tile_map = {}
        seq = 0
        while True:
            tile = fp.read(8)
            if not tile:
                break
            if tile == "AAAAAAAA":
                z, x = divmod(seq, 250)
                rect = ((x*6, z*6), (x*6+5, z*6+5))
                draw.rectangle(rect, outline="#44cef6", fill="#44cef6")
            if tile in tile_map:
                tile_map[tile] += 1
            else:
                tile_map[tile] = 1
            seq += 1
    return im


def draw_tiles(tiles, im=None):
    if im is None:
        im = Image.new("RGB", (WIDTH, HEIGHT), color="#FEFEFE")
    draw = ImageDraw.Draw(im)
    empty_color = set()
    for idx, tile in enumerate(tiles):
        z, x = divmod(idx, WIDTH/4)
        z = z*4
        x = x*4
        rect = ((x, (HEIGHT-z)-1), (x+3, HEIGHT-(z+3)-1))
        tile_name = TILE_ID_REVERSE_MAP[tile]
        color = TILE_COLOR_MAP[tile_name]
        if type(color) is int:
            empty_color.add(color)
            color = '#f2ecde'
        draw.rectangle(rect, outline=color, fill=color)
    print(empty_color)
    return im


def draw_nodes(nodes, im=None):
    if im is None:
        im = Image.new("RGB", (WIDTH, HEIGHT), color="#FEFEFE")
    draw = ImageDraw.Draw(im)
    for node in nodes:
        poly_to_trans = node.get('poly')
        poly = list(map(coord2, poly_to_trans))
        draw.polygon(poly, outline="#010101")
    return im


def draw_roads(roads, im=None):
    if im is None:
        im = Image.new("RGB", (WIDTH, HEIGHT), color="#FEFEFE")
    draw = ImageDraw.Draw(im)
    for road in roads:
        if road:
            lines_to_trans = road[1:]
            lines = list(map(coord2, lines_to_trans))
        draw.line(lines, fill="#373737", width=3)
    return im


def coord1(crd):  # canvas to map
    x, z = crd
    return x - WIDTH/2, HEIGHT/2 - z


def coord2(crd):  # map to canvas
    x, z = crd
    return (x + WIDTH/2), (HEIGHT/2 - z)