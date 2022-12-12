import os
import sys
import json

from PIL import Image, ImageDraw, ImageFont

cwd = os.path.dirname(__file__)
sys.path.append(cwd)
from parse_dst_xml import get_image
from parse_tunings import get_tunings


BACKPACK_MAPPING = {
    'backpack': 8,
    'icepack': 8,
    'seedpouch': 14,
    'candybag': 14,
    'spicepack': 6,
    'krampus_sack': 14,
    'piggyback': 12,
}

margin = 70
padding = 3
fnt_small = ImageFont.truetype("Pillow/Tests/fonts/FreeMono.ttf", 24)

top_padding = 30
small_gap = 7
middle_gap = 14
left_margin = 30
right_margin = 30
head_icon_resize = 74
inv_slot_resize = 58

TUNINGS = get_tunings()


def draw_inv(userdata):
    data = userdata.get('data')
    if not data:
        return None
    prefab = userdata['prefab']
    im, positions = draw_background()
    # draw head icon
    if data.get('is_ghost'):
        head_icon = get_image(f"avatar_ghost_{prefab}")
    else:
        head_icon = get_image(f"avatar_{prefab}")
    head_icon.thumbnail((inv_slot_resize, inv_slot_resize))
    pos = positions['head_icon']
    im.alpha_composite(head_icon, dest=pos)
    bundle_y_start = top_padding + inv_slot_resize + middle_gap
    # draw inventory
    inventory = data['inventory']
    items = inventory['items']
    inv_pos = positions['inv']
    bundles = []
    for idx, item in enumerate(items):
        if item:  # None if empty
            pos = inv_pos[idx]
            draw_item(im=im, pos=pos, item_info=item)
            if item['prefab'] in ("bundle", "gift"):
                bundles.append(item)
    # draw equip
    equip = inventory['equip']
    for idx, part in enumerate(('hands', 'body', 'head')):
        if not equip:
            break
        equip_item = equip.get(part)
        if equip_item:
            pos = positions['equip'][idx]
            draw_item(im=im, pos=pos, item_info=equip_item)
            if part == 'body' and \
                    equip_item.get('data', {}).get('container'):
                bundle_y_start += small_gap + inv_slot_resize
                backpack_name = equip_item['prefab']
                if backpack_name in BACKPACK_MAPPING:
                    slot_num = BACKPACK_MAPPING[backpack_name]
                    contained = equip_item['data']['container']['items']
                    inv_slot_im = get_image("inv_slot")
                    inv_slot_im.thumbnail(
                            (inv_slot_resize, inv_slot_resize))
                    # draw backpack slots
                    for idx in range(slot_num):
                        pos = (inv_pos[15-slot_num+idx][0], 
                            top_padding+inv_slot_resize+small_gap)
                        im.alpha_composite(inv_slot_im, dest=pos)
                        item = contained[idx] if idx < len(contained) else None
                        if item:
                            # draw backpack
                            draw_item(im=im, pos=pos, item_info=item)
                            if item['prefab'] in ("bundle", "gift"):
                                bundles.append(item)
                else:
                    print(f"UNINCLUDED backpack type: {backpack_name}")
    # draw bundles
    if bundles:
        bundle_padding = 27
        filling_height = 180
        im_inv_bg = get_image("inventory_bg")
        im_filling = im_inv_bg.crop((
            0, 
            im_inv_bg.height - filling_height, 
            im_inv_bg.width, 
            im_inv_bg.height
        ))
        del im_inv_bg
        im_bundle_bg, ords = draw_bundle_bg()
        nums = 6
        bl_margin = (
                im.width - nums*im_bundle_bg.width - (nums-1)*bundle_padding)/2
        bl_margin = int(bl_margin)
        bundle_records = []
        for idx, bundle_info in enumerate(bundles):
            offset = (
                bl_margin+(idx%nums)*(im_bundle_bg.width+bundle_padding), 
                bundle_y_start+(idx//nums)*(im_bundle_bg.height+bundle_padding)
            )
            items = bundle_info['data']['unwrappable']['items']
            bundle_records.append((items, offset))
        bundle_levels = idx // nums + 1
        new_height = bundle_y_start + \
                bundle_levels * (im_bundle_bg.height + bundle_padding)
        h_diff = new_height - im.height
        filling_num, filling_rest = divmod(h_diff, filling_height)
        new_im = Image.new("RGBA", (im.width, new_height), (0,0,0,0))
        new_im.alpha_composite(im, (0, 0))
        for i in range(filling_num):
            new_im.alpha_composite(im_filling, (0, im.height+i*filling_height))
        if filling_rest:
            new_im.alpha_composite(im_filling, 
                (0, im.height+filling_num*filling_height),
                (0, 0, im.width, filling_rest),    
            )
        del im
        im = new_im
        for items, offset in bundle_records:
            im.alpha_composite(im_bundle_bg, offset)
            for i, item in enumerate(items):
                ord = ords[i]
                pos = (offset[0]+ord[0], offset[1]+ord[1])
                draw_item(im, pos, item)
    return im


def draw_background():
    bg = get_image("inventory_bg")
    inv_bg = get_image("inv_slot")
    inv_bg.thumbnail((inv_slot_resize, inv_slot_resize))
    positions = {}
    # draw inventory slots
    positions['inv'] = []
    for i in range(15):
        pos = (
            left_margin + i*small_gap + (i//5)*middle_gap + i*inv_bg.width, 
            top_padding,
        )
        positions['inv'].append(pos)
        bg.alpha_composite(inv_bg, dest=pos)
    # draw equip
    equip_pos = (pos[0]+middle_gap, top_padding)
    positions['equip'] = []
    for idx, equip in enumerate(("", "_body", "_head")):
        equip_bg = get_image(f"equip_slot{equip}")
        equip_bg.thumbnail((inv_slot_resize, inv_slot_resize))
        _pos = (equip_pos[0]+idx*small_gap+inv_slot_resize*(1+idx), 
                    equip_pos[1]
            )
        bg.alpha_composite(equip_bg, dest=_pos)
        positions['equip'].append(_pos)
    # draw head icon
    head_bg = get_image("button_square")
    head_bg.thumbnail((head_icon_resize, head_icon_resize))
    _pos = (bg.width-right_margin-head_bg.width, top_padding)
    bg.alpha_composite(head_bg, dest=_pos)
    positions['head_icon'] = _pos
    return bg, positions


def fix_prefab(item_info):
    prefab = item_info['prefab']
    fmt = "{prefab}"
    if prefab in ("bundle", "gift") or prefab.startswith("redpouch"):
        bundled_items = item_info['data']['unwrappable']['items']
        if len(bundled_items) == 1:
            fmt = "{prefab}_small"
        elif len(bundled_items) in (2, 3):
            fmt = "{prefab}_medium"
        elif len(bundled_items) == 4:
            fmt = "{prefab}_large"
        else:
            print(f"UNEXPECTED num {len(bundled_items)} for bundle")
        variation = item_info.get('data', {}).get("variation")
        if variation:
            fmt += str(variation)
    elif prefab in ("onion", "onion_cooked"):
        fmt = f"quagmire_{prefab}"  # yes, it should have been formatted!
    elif prefab == "cursed_monkey_token":
        image_num = item_info['data']['image_num']
        fmt = f"cursed_beads{image_num}"
    elif prefab == "rock_avocado_fruit":
        fmt = "rock_avocado_fruit_ripe"
    elif prefab == "rock_avocado_fruit_cooked":
        fmt = "rock_avocado_fruit_ripe_cooked"
    return fmt


def draw_bundle_bg():
    height = 190
    im = im_right_top = get_image("inventory_corner")
    im_left_top = im.transpose(Image.FLIP_LEFT_RIGHT)
    im_right_bot = im.transpose(Image.FLIP_TOP_BOTTOM)
    im_left_bot = im.transpose(Image.ROTATE_180)
    im_filler_top = get_image("inventory_filler")
    im_filler_bot = im_filler_top.transpose(Image.FLIP_TOP_BOTTOM)
    top_crop = (0, 0, im.width, height/2)
    im_bg = Image.new("RGBA", 
        (im_left_top.width+im_filler_top.width+im_right_top.width, height),
        color=(0,0,0,0),
    )
    im_bg.alpha_composite(im_left_top, (0,0), top_crop)
    im_bg.alpha_composite(im_filler_top, (im_left_top.width, 0), top_crop)
    im_bg.alpha_composite(im_right_top, (im_left_top.width+im_filler_top.width, 0), top_crop)
    paste_y = int(height/2)
    bot_crop = (0, int(paste_y-(height-im.height)), im.width, im.height)
    im_bg.alpha_composite(im_left_bot, (0, paste_y), bot_crop)
    im_bg.alpha_composite(im_filler_bot, (im_left_bot.width, paste_y), bot_crop)
    im_bg.alpha_composite(im_right_bot, (im_left_bot.width+im_filler_bot.width, paste_y), bot_crop)
    dec_scale = 0.5
    im_dec_bot = get_image("craft_end_short")
    im_dec_bot.thumbnail(
            (im_dec_bot.width*dec_scale, im_dec_bot.height*dec_scale))
    im_dec_top = im_dec_bot.transpose(Image.FLIP_TOP_BOTTOM)
    dec_x = int(im_bg.width/2 - im_dec_bot.width/2)
    im_bg.alpha_composite(im_dec_top, (dec_x, 0))
    im_bg.alpha_composite(im_dec_bot, (dec_x, im_bg.height-im_dec_bot.height))
    padding = 34
    im_slot = get_image("inv_slot")
    im_slot.thumbnail((inv_slot_resize, inv_slot_resize))
    cords = (
        (padding, padding),
        (padding, height-padding-im_slot.height),
        (im_bg.width-padding-im_slot.width, padding),
        (im_bg.width-padding-im_slot.width, height-padding-im_slot.height),
    )
    im_bg.alpha_composite(im_slot, cords[0])
    im_bg.alpha_composite(im_slot, cords[1])
    im_bg.alpha_composite(im_slot, cords[2])
    im_bg.alpha_composite(im_slot, cords[3])
    return im_bg, cords

def draw_item(im, pos, item_info):
    with open(os.path.join(cwd, "inv_images_infos.json"), 'r') as fp:
        img_infos = json.load(fp)
    prefab = item_info['prefab']
    fixed_format = fix_prefab(item_info)
    skinname = item_info.get('skinname', prefab)
    prefab = fixed_format.format(prefab=prefab)
    skinname = fixed_format.format(prefab=skinname)
    spiced = False
    if "_spice_" in prefab:
        spiced = True
        food, spice = prefab.split("_spice_")
        spice_prefab = f"spice_{spice}_over"
        skinname = prefab = food
    image = get_image(skinname) or get_image(prefab)
    if not image:
        print(f"cant draw item {prefab}: {item_info}")
        return
    if spiced:
        im_spice = get_image(spice_prefab)
        if im_spice:
            image.alpha_composite(im_spice)
        else:
            print(f"cant find spice {spice_prefab}")
    image.thumbnail((inv_slot_resize, inv_slot_resize))
    im.alpha_composite(image, pos)
    draw = ImageDraw.Draw(im)
    if item_info.get('data', {}).get('stackable'):
        stack = item_info['data']['stackable']['stack']
        draw.text(
            (pos[0]+inv_slot_resize/2, pos[1]), 
            str(stack), 
            font=fnt_small,
            fill=(255, 255, 255, 255),
            stroke_fill=(0, 0, 0, 255),
            stroke_width=1,
            anchor="ma",
        )
    text = ""
    if item_info.get('data', {}).get('finiteuses'):
        uses = item_info['data']['finiteuses']['uses']
        max_use = TUNINGS.get(f"{item_info['prefab']}_uses".upper())
        if max_use:
            text = f"{uses/max_use:.0%}"
    elif item_info.get('data', {}).get("fueled"):
        fuel = item_info['data']['fueled']['fuel']
        max_fuel = TUNINGS.get(f"{item_info['prefab']}_perishtime".upper())
        if max_fuel:
            text = f"{fuel/max_fuel:.0%}"
    elif item_info.get('data', {}).get('armor'):
        armor = item_info['data']['armor']['condition']
        max_armor = TUNINGS.get(f"armor_{item_info['prefab']}".upper())
        if max_armor:
            text = f"{armor/max_armor:.0%}"
    if text:
        draw.text(
            (pos[0]+inv_slot_resize, pos[1]+inv_slot_resize),
            text,
            font=fnt_small,
            fill=(255, 255, 255, 255),
            stroke_fill=(0, 0, 0, 255),
            stroke_width=1,
            anchor="rd",
        )

def merge_inv_images(ims):
    height = sum(map(lambda x: x.height, ims))
    width = ims[0].width
    image = Image.new("RGBA", (width, height))
    h = 0
    for im in ims:
        image.paste(im, (0, h))
        h += im.height
    return image


if __name__ == "__main__":
    from parse_save import get_latest_save, parse_user
    from manage_user import session_to_ku, ku_to_name
    fnt_info = ImageFont.truetype(
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", size=30)
    saves = get_latest_save(user=True)
    users_save = saves['user']
    ims = []
    for user_session, entry in users_save.items():
        ku = session_to_ku(user_session)
        name = ku_to_name(ku)
        userdata = parse_user(entry.path)
        im = draw_inv(userdata)
        if im:
            d = ImageDraw.Draw(im)
            d.text((im.width-100, im.height), f"{ku}: {name}", 
                fill="#010101", font=fnt_info, anchor="rd")
            ims.append(im)
    big_im = merge_inv_images(ims)
    big_im.show()
    big_im.save("big_im.png")
    # im, positions = draw_background()
    # im.show()
    # im = draw_bundle_bg()
    # im.show()