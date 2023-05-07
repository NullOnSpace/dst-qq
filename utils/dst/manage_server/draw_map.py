import os
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

cwd = os.path.dirname(__file__)
sys.path.append(cwd)

from get_config import INSTALL_DIR
from get_prefab_list import PREFABS as ENT_TRANSLATION
from parse_save import parse_map_nav
from prefab_to_icon import MAPPING

ICONS_PNG_PATH = os.path.join(cwd, "minimap_atlas.png")


fnt_imp = ImageFont.truetype(
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", size=30)
fnt_info = ImageFont.truetype(
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", size=24)


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
    CHECKER=12,
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


def parse_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    t = parse_xml_ele(root)
    return t

def parse_xml_ele(xml_ele):
    obj = {}
    obj['tag'] = xml_ele.tag
    obj['attrib'] = xml_ele.attrib
    if len(xml_ele):
        obj['children'] = children = []
        for child in xml_ele:
            c = parse_xml_ele(child)
            children.append(c)
    return obj

def get_map_icon_infos():
    # return {"png_name": {"png_name":png_name, "u1": u1...}}
    xml_path = os.path.join(INSTALL_DIR, 'data/minimap/minimap_data.xml')
    datas = parse_xml(xml_path)
    icon_eles = datas['children'][1]['children']
    icon_mapping = {}
    for icon_ele in icon_eles:
        attr = icon_ele['attrib']
        name = attr['name']
        icon_mapping[name] = attr
    return icon_mapping

def get_map_icon(icon_name, icon_infos=None):
    if icon_infos is None:
        icon_infos = get_map_icon_infos()
    if icon_name in icon_infos:
        icon_png = Image.open(ICONS_PNG_PATH)
        height = icon_png.height
        width = icon_png.width
        attr = icon_infos[icon_name]
        u1 = float(attr['u1'])*width
        u2 = float(attr['u2'])*width
        v2 = (1-float(attr['v1']))*height
        v1 = (1-float(attr['v2']))*height
        icon = icon_png.crop((u1, v1, u2, v2))
    return icon


def draw_icon(im, prefab, pos, icon_infos=None, icon_lib=None):
    if icon_infos is None:
        icon_infos = get_map_icon_infos()
    scale = 0.25
    anchor = (0.5, 0)
    if prefab in MAPPING:
        png_name = MAPPING[prefab].get('name', prefab) + '.png'
        scale = MAPPING[prefab].get('scale', scale)
        anchor = MAPPING[prefab].get('anchor', anchor)
    elif prefab+".png" in icon_infos:
        png_name = prefab + ".png"
    else:
        png_name = None
    if png_name:
        if icon_lib and png_name in icon_lib:
            icon_im = icon_lib[png_name]
        else:
            icon_im = get_map_icon(png_name)
            icon_im.thumbnail((icon_im.width*scale, icon_im.height*scale))
            if icon_lib is not None:
                icon_lib[png_name] = icon_im
        anchor_x, anchor_y = anchor
        im.alpha_composite(
            icon_im, 
            (int(pos[0])-int(icon_im.width*anchor_x),
                    int(pos[1])-int(icon_im.height*(1-anchor_y))),
        )
        return True
    else:
        return False
    

def draw_icons(savedata, im=None, width=None, height=None):
    if not (im or (width and height)):
        raise ValueError("None of im or size")
    if width is None:
        width = im.width
    else:
        width = width*4
    if height is None:
        height = im.height
    else:
        height = height*4
    if im is None:
        im = Image.new("RGB", (width, height), color="#FEFEFE")
    draw = ImageDraw.Draw(im)
    icon_infos = get_map_icon_infos()
    ents = savedata["ents"]
    icon_lib = {}
    for prefab, details in ents.items():
        if prefab in ("wormhole", "tentacle_pillar", "tentacle_pillar_hole"):
            _draw_wormholes(details, im, prefab)
            continue
        if details is None:
            continue
        for detail in details:
            x = detail.get("x")
            z = detail.get("z")
            crd = coord2((x, z), width=width, height=height)
            has_icon = draw_icon(im, prefab, crd, 
                    icon_infos=icon_infos, icon_lib=icon_lib)
            if not has_icon:
                draw.rectangle(
                    [(crd[0]-1, crd[1]+1), (crd[0]+1, crd[1]-1)], 
                    outline="#010101")
                ent_name = ENT_TRANSLATION.get(prefab, prefab)
                draw.text(crd, 
                        ent_name, fill="#010101", anchor="md", font=fnt_imp)
    return im


def draw_ents(savedata, im=None, width=None, height=None):
    if not (im or (width and height)):
        raise ValueError("None of im or size")
    if width is None:
        width = im.width
    else:
        width = width*4
    if height is None:
        height = im.height
    else:
        height = height*4
    if im is None:
        im = Image.new("RGB", (width, height), color="#FEFEFE")
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
            crd = coord2((x, z), width=width, height=height)
            draw.rectangle(
                [(crd[0]-1, crd[1]+1), (crd[0]+1, crd[1]-1)], 
                outline="#010101")
            draw.text(crd, ent_name, fill="#010101", anchor="md", font=fnt_imp)
    return im


def _draw_wormholes(worms, im, prefab, icon_infos=None):
    if icon_infos is None:
        icon_infos = get_map_icon_infos()
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
        crd = coord2((x, z), width=im.width, height=im.height)
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
        has_icon = draw_icon(im, prefab, crd, icon_infos=icon_infos)
        if not has_icon:
            draw.rectangle(
                    [(crd[0]-3, crd[1]+3), (crd[0]+3, crd[1]-3)], 
                    outline=color, fill=color)
        name = ENT_TRANSLATION.get(prefab, prefab)
        draw.text(crd, name+str(serial), 
                fill="#010101", anchor="md", font=fnt_info)


def draw_background(map_file, im=None, width=None, height=None):
    if not (im or (width and height)):
        raise ValueError("None of im or size")
    if width == None:
        width = im.width
    else:
        width = width*4
    if height == None:
        height = im.height
    else:
        height = height*4
    if im is None:
        im = Image.new("RGB", (width, height), color="#FEFEFE")
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


def draw_tiles(tiles, im=None, width=None, height=None):
    if not (im or (width and height)):
        raise ValueError("None of im or size")
    if width == None:
        width = im.width
    else:
        width = width*4
    if height == None:
        height = im.height
    else:
        height = height*4
    if im is None:
        im = Image.new("RGBA", (width, height), color="#FEFEFE")
    draw = ImageDraw.Draw(im)
    empty_color = set()
    unknown_tiles = set()
    for idx, tile in enumerate(tiles):
        z, x = divmod(idx, width/4)
        z = z*4
        x = x*4
        rect = ((x, (height-z)-1), (x+3, height-(z+3)-1))
        tile_name = TILE_ID_REVERSE_MAP.get(tile, "unknown")
        if tile_name == "unknown":
            unknown_tiles.add(tile)
        color = TILE_COLOR_MAP.get(tile_name, "#030303")
        if type(color) is int:
            empty_color.add(color)
            color = '#f2ecde'
        draw.rectangle(rect, outline=color, fill=color)
    print("unset tile id:", empty_color)
    print("unknown tile id:", unknown_tiles)
    return im


def draw_nodes(nodes, im=None, width=None, height=None):
    if not (im or (width and height)):
        raise ValueError("None of im or size")
    if width:
        width = width*4
    if height:
        height = height*4
    if im is None:
        im = Image.new("RGB", (width, height), color="#FEFEFE")
    draw = ImageDraw.Draw(im)
    for node in nodes:
        poly_to_trans = node.get('poly')
        poly = list(map(coord2, poly_to_trans))
        draw.polygon(poly, outline="#010101")
    return im


def draw_roads(roads, im=None, width=None, height=None):
    if width:
        width = width*4
    if height:
        height = height*4
    if im is None:
        im = Image.new("RGB", (width, height), color="#FEFEFE")
    draw = ImageDraw.Draw(im)
    for road in roads:
        if road:
            lines_to_trans = road[1:]
            lines = list(map(coord2, lines_to_trans))
        draw.line(lines, fill="#373737", width=3)
    return im


def coord2(crd, width, height):
    # map to canvas
    x, z = crd
    return (x + width/2), (height/2 - z)


if __name__ == "__main__":
    # from parse_save import parse
    # with open(os.path.join(cwd, "temp/0000000002")) as fp:
    #     savedata = parse(fp, ents_level=2,
    #          extra_ents=(k for k, v in MAPPING.items() if v.get('draw', True)))
    # tiles = parse_map_nav(savedata['map']['tiles'])
    # height = savedata['map']['height']
    # width = savedata['map']['width']
    # im = draw_tiles(tiles, width=width, height=height)
    # im = draw_icons(savedata, im=im)
    # im.show()
    # im.save(os.path.join(cwd, "temp/master_map.png"))


    # im = get_map_icon('toadstool_hole.png')
    # im.show()

    for k in sorted(TILE_ID_REVERSE_MAP):
        print(k, TILE_ID_REVERSE_MAP[k])