import py7zr

import shutil
import configparser
import time
import os
CWD = os.path.dirname(__file__)

from parse_save import parse, parse_map_nav, get_latest_save
from draw_map import draw_ents, draw_tiles


def handle_savefile(save_file_path):
    # handle a savefile and return im of map and seed and days
    with open(save_file_path, 'r') as fp:
        data = parse(fp, ents_level=1)
    try:
        seed = str(data['meta']['seed'])
    except KeyError:
        seed = '0'
    try:
        cycles = data['persistedate']['worldstate']['cycles']
    except KeyError:
        cycles = 0
    info = {'seed': seed, 'days': str(cycles+1)}
    tiles = parse_map_nav(data['map']['tiles'])
    height = data['map']['height']
    width = data['map']['width']
    im = draw_tiles(tiles, width=width, height=height)
    im = draw_ents(data, im=im)
    info.update(map=im)
    return info


def zip_cluster(cluster_dir):
    print(f"zipping cluster {cluster_dir}")
    parent = os.path.dirname(cluster_dir)
    save = get_latest_save(cluster=cluster_dir)
    print(f"fetch latest save: {save}")
    cluster_ini_path = os.path.join(cluster_dir, 'cluster.ini')
    config = configparser.ConfigParser()
    config.read(cluster_ini_path)
    name = config['NETWORK']['cluster_name']
    name_safe = name.replace(" ", "_")
    maps = []
    for level, save_file in save.items():
        i = handle_savefile(save_file)
        level_dir = os.path.join(cluster_dir, level)
        map_name = 's'+i['seed']+'_d'+i['days']+"_"+level+".png"
        map_path = os.path.join(level_dir, map_name)
        i['map'].save(map_path)
        maps.append(map_path)
        print(f"{level}:{save_file.name} seed:{i['seed']} days:{i['days']}")
        print(f"draw map for {level} in {map_path}")
    temp_cluster = time.strftime(f"{name_safe}_{i['seed']}_%y%m%d%H%M%S")
    temp_cluster_dir = os.path.join(parent, temp_cluster)
    print(f"copy to {temp_cluster_dir}")
    shutil.copytree(cluster_dir, temp_cluster_dir)
    purge_cluster(temp_cluster_dir)
    print("purge cluster folder success")
    print("zip file now")
    filename_7z = time.strftime(
            f"{name_safe}_%y%m%d%H%M_d{i['days']}_s{i['seed']}.7z")
    path_7z = os.path.join(os.path.dirname(cluster_dir), filename_7z)
    with py7zr.SevenZipFile(path_7z, 'w') as archive:
        archive.writeall(temp_cluster_dir, arcname='MyDediServer')
    print(f"archive file: {path_7z}")
    print("zip cluster success")
    f = {
        'maps': maps, '7z': path_7z, 'temp_dir': temp_cluster_dir,
    }
    return f


def purge_cluster(cluster_dir):
    # remove admin, black, whitelist, token, remove logs, and rebundent info in cluster.ini
    print(f"purge for {cluster_dir}")
    for entry in os.scandir(cluster_dir):
        if ".txt" in entry.name:
            os.remove(entry.path)
            print(f"remove {entry.name} in cluster root")
    for level in ('Master', 'Caves'):
        level_dir = os.path.join(cluster_dir, level)
        # remove log
        for entry in os.scandir(level_dir):
            if entry.name.endswith('.txt'):
                os.remove(entry.path)
                print(f"remove log: {entry.path}")
        backup_dir = os.path.join(level_dir, 'backup')
        if os.path.exists(backup_dir):
            print(f"remove backup dir: {backup_dir}")
            shutil.rmtree(backup_dir)
    cluster_ini_path = os.path.join(cluster_dir, 'cluster.ini')
    config = configparser.ConfigParser()
    config.read(cluster_ini_path)
    name = config['NETWORK']['cluster_name']
    new_desc = time.strftime(f"{name}_备份存档_%y%m%d%H%M")
    config['NETWORK']['cluster_description'] = new_desc
    print(f"mod description to: {new_desc}")
    if 'steam' in config:
        del config['steam']
        print("delete [steam] in config")
    with open(cluster_ini_path, 'w') as fp:
        config.write(fp)
        print("rewrite config file")


def main():
    cluster_dir = '/home/hikaru/.klei/DoNotStarveTogether/MyDediServer_10171741'
    zip_cluster(cluster_dir)


if __name__ == "__main__":
    main()
