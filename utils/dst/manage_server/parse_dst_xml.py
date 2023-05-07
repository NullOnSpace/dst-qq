import os
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

cwd = os.path.dirname(__file__)
sys.path.append(cwd)

from get_config import INSTALL_DIR
from draw_map import parse_xml

def parse(xml_name, dir=os.path.join(INSTALL_DIR, 'data/databundles/images')):
    xml_path = os.path.join(dir, xml_name+".xml")
    if not os.path.exists(xml_path):
        return
    datas = parse_xml(xml_path)
    info_eles = datas['children'][1]['children']
    mapping = {}
    for info in info_eles:
        attr = info['attrib']
        name = attr['name']
        mapping[name] = attr
    return mapping


def draw_schema(xml_info):
    w, h = (2048, 2048)
    schema = Image.new("RGB", size=(w, h), color=(255,255,255))
    draw = ImageDraw.Draw(schema)
    font = ImageFont.truetype("Tests/fonts/NotoSans-Regular.ttf", 18)
    for k, v in xml_info.items():
        left = w*float(v['u1'])
        right = w*float(v['u2'])
        bottom = h*(1-float(v['v1']))
        top = h*(1-float(v['v2']))
        draw.rectangle((left, top, right, bottom), outline=(0,0,0))
        draw.text(
            ((left+right)/2, top), 
            k[:-4], anchor="ma", fill=(0,0,0),
            font=font,
        )
        draw.text(
            ((left+right)/2, (top+bottom)/2),
            str(right-left)+"*"+str(bottom-top), anchor="mm", fill=(0,0,0),
            font=font,
        )
    return schema

def get_total_infos():
    p = os.path.join(INSTALL_DIR, 'data/databundles/images')
    total_infos = {}
    for entry in os.scandir(p):
        if entry.name.endswith(".xml"):
            d = parse(entry.name[:-4])
            for v in d.values():
                v['source'] = entry.path
            total_infos.update(d)
    return total_infos
            

def get_image(image_name, img_dir="/home/hikaru/ktools/images"):
    total_infos = get_total_infos()
    tex_name = image_name+".tex"
    if not tex_name in total_infos:
        print(f"cant find {tex_name} in total infos")
        return
    info = total_infos[tex_name]
    source = info['source']
    img_path = os.path.join(
        img_dir,
        source[:-4].split("/")[-1]+".png"
    )
    image_png = Image.open(img_path)
    height = image_png.height
    width = image_png.width
    u1 = float(info['u1'])*width
    u2 = float(info['u2'])*width
    v2 = (1-float(info['v1']))*height
    v1 = (1-float(info['v2']))*height
    im = image_png.crop((u1, v1, u2, v2))
    return im


if __name__ == "__main__":
    pass
    # im = get_image("inventory_corner")
    # im.show()

    i = parse("hud")
    print(i)
    m = draw_schema(i)
    m.show()