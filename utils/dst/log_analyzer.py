import re
import pprint
# analyze log in dst


def main():
    AUTH_PATTERN = re.compile("Client authenticated: \((?P<ku>[\w\d\-_]+)\) (?P<name>.+)$")
    IP_PATTERN = re.compile("New incoming connection (?P<ip>[\d+.]+)\|\d+ <(?P<uid>\d+)>$")
    with open("log.txt", 'r+b') as fp:
        ku_dict = {}
        ip = ""
        uid = ""
        ip_lineno = 0
        for lineno, b_line in enumerate(fp):
            try:
                line = b_line.decode("utf8")
            except UnicodeDecodeError:
                continue
            if AUTH_PATTERN.search(line):
                match = AUTH_PATTERN.search(line)
                ku = match.group("ku")
                name = match.group("name")
                if ku in ku_dict:
                    name_list = ku_dict[ku]['name_list']
                    ip_list = ku_dict[ku]["ip_list"]
                    uid_list = ku_dict[ku]["uid_list"]
                    ku_dict[ku]["access_count"] += 1
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
                        'access_count': 1,
                    }
                ip = ""
                uid = ""
                if lineno - ip_lineno > 4:
                    print(f"[WARN]match line:{ip_lineno} with line:{lineno}")
            elif IP_PATTERN.search(line):
                match = IP_PATTERN.search(line)
                ip = match.group("ip")
                uid = match.group("uid")
                ip_lineno = lineno
            else:
                pass
    pprint.pprint(ku_dict)

if __name__ == '__main__':
    main()
