import copy
import os
import json


CWD = os.path.dirname(__file__)

def char_to_base64(ch):
    if ord(ch) >= ord("A") and ord(ch) <= ord("Z"):
        return ord(ch) - 55
    elif ord(ch) >= ord("a") and ord(ch) <= ord("z"):
        return ord(ch) - 97 + 36
    elif ch == "-":
        return 62
    elif ch == "_":
        return 63
    elif ch.isdigit():
        return ord(ch) - 48
    else:
        raise ValueError(f"cant parse {ch} to base64")

def char_to_base32(ch):
    if ord(ch) >= ord("A") and ord(ch) <= ord("V"):
        return ord(ch) - 55
    elif ch.isdigit():
        return ord(ch) - 48
    else:
        raise ValueError(f"cant parse {ch} to base32")

def base64_to_char(i):
    if i >= 10 and i <= 35:
        return chr(i + 55)
    elif i >= 36 and i <= 61:
        return chr(i + 61)
    elif i >= 0 and i <= 10:
        return str(i)
    elif i == 62:
        return "-"
    elif i == 63:
        return "_"

def base64s_to_str(bs):
    bin_str = ("{:08b}"*len(bs)).format(*[b for b in bs])
    return bin_str_to_ku(bin_str)

def bin_str_to_ku(b):
    # b is a number in str form like "011010110100"
    s = ""
    while True:
        if b:
            sub_s = b[:6]
            s += base64_to_char(int(sub_s, base=2))
            b = b[6:]
        else:
            break
    return s

def session_to_ku(s):
    return bin_str_to_ku(get_bin_32(s))

def get_bin_64(s):
    return ("{:06b}"*len(s)).format(*[char_to_base64(i) for i in s])

def get_bin_32(s):
    return ("{:05b}"*len(s)).format(*[char_to_base32(i) for i in s])


def ku_to_name(ku):
    full_ku = ku[:2] + "_" + ku[2:]
    ku_path = os.path.join(CWD, 'temp', 'ku_dict.json')
    with open(ku_path, 'r') as fp:
        ku_dict = json.load(fp)
    if full_ku in ku_dict:
        name = ku_dict[full_ku]['name_list'][0]
        return name
    else:
        return ku