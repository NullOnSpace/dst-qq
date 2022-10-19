import re
import pprint
import os
# analyze log in dst


def analyze(log_path):
    AUTH_PATTERN = re.compile("Client authenticated: \((?P<ku>[\w\d\-_]+)\) (?P<name>.+)$")
    IP_PATTERN = re.compile("New incoming connection (?P<ip>[\d+.]+)\|\d+ <(?P<uid>\d+)>$")
    START_TIME_PATTERN = re.compile("Current time: (?P<time>.+)")
    TIME_PATTERN = re.compile("^(?P<time>\[d+:\d+:\d+\])")
    with open(log_path, 'rb') as fp:
        ku_dict = {}
        ip = ""
        uid = ""
        ip_lineno = 0
        for lineno, b_line in enumerate(fp):
            try:
                line = b_line.decode("utf8", errors='ignore')
            except UnicodeDecodeError:
                continue
            if AUTH_PATTERN.search(line):
                match = AUTH_PATTERN.search(line)
                ku = match.group("ku")
                name = match.group("name").strip('\r')
                if ku in ku_dict:
                    name_list = ku_dict[ku]['name_list']
                    ip_list = ku_dict[ku]["ip_list"]
                    uid_list = ku_dict[ku]["uid_list"]
                    if name not in name_list:
                        name_list.append(name)
                    if ip not in ip_list:
                        ip_list.append(ip)
                    if uid not in uid_list:
                        uid_list.append(uid)
                else:
                    ku_dict[ku] = {
                        'name_list':[name],
                        'ip_list':[ip],
                        'uid_list':[uid],
                    }
                ip = ""
                uid = ""
                if lineno - ip_lineno > 20:
                    print(f"[WARN]match line:{ip_lineno} with line:{lineno}")
            elif IP_PATTERN.search(line):
                match = IP_PATTERN.search(line)
                ip = match.group("ip")
                uid = match.group("uid")
                ip_lineno = lineno
            else:
                pass
    return ku_dict


def merge_ku_dict(*ku_ds):
    result = {}
    for ku_d in ku_ds:
        for ku, record in ku_d.items():
            record_total = result.setdefault(ku, {})
            for info in ('ip_list', 'name_list', 'uid_list'):
                total = record_total.get(info, [])
                record_total[info] = list(
                    set(total).union(record[info])
                )
    return result


def recursive_scan(dir):
    ds = []
    for entry in os.scandir(dir):
        if entry.is_file() and entry.name.startswith("server_log"):
            ds.append(analyze(entry.path))
        elif entry.is_dir():
            ds.extend(recursive_scan(entry.path))
    return ds


if __name__ == '__main__':
    cwd = os.path.dirname(__file__)
    # ds = recursive_scan(cwd)
    # kud = merge_ku_dict(*ds)
    import json
    # with open(os.path.join(cwd, 'ku_dict.json'), 'w') as fp:
    #     json.dump(kud, fp, ensure_ascii=False, indent=2)
    p1 = '/home/hikaru/qqbot/utils/dst/manage_server/ku_dict.json'
    p2 = '/home/hikaru/.klei/DoNotStarveTogether/ku_dict.json'
    with open(p1, 'r') as fp:
        ku_d1 = json.load(fp)
    with open(p2, 'r') as fp:
        ku_d2 = json.load(fp)
    ku_d = merge_ku_dict(ku_d1, ku_d2)
    with open(os.path.join(cwd, 'total_ku.json'), 'w') as fp:
        json.dump(ku_d, fp, ensure_ascii=False, indent=2)
