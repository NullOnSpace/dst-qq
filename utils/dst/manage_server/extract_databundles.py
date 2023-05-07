import xml.etree.ElementTree as ET
import os
import sys

cwd = os.path.dirname(__file__)
sys.path.append(cwd)

from draw_map import parse_xml
from get_config import INSTALL_DIR


def get_inv_images_icon_infos():
    xml_path_pre = "data/databundles/images"
    fname_tpl = "inventoryimages{}.xml"
    infos = {}
    for i in ('1', '2', '3'):
        p = os.path.join(INSTALL_DIR, xml_path_pre, fname_tpl.format(i))
        datas = parse_xml(p)
        icon_eles = datas['children'][1]['children']
        for icon_ele in icon_eles:
            attr = icon_ele['attrib']
            name = attr['name']
            attr['group'] = i
            if name[-4:] == ".tex":
                prefab = name[:-4]
                infos[prefab] = attr
            else:
                print(f"not ends with '.tex' for {name}")
    return infos


if __name__ == "__main__":
    import json
    infos = get_inv_images_icon_infos()
    with open("inv_images_infos.json", 'w') as fp:
        json.dump(infos, fp, indent=2, sort_keys=True)