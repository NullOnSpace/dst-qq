import requests

def main():
    URL1 = "https://api.dstserverlist.top/api/list"
    HOST = "KU_3RvV9haR"
    payload = {'name': "旺旺旺", "pageCount":100, 'page':0}
    res = requests.post(URL1, params=payload, data=payload)
    URL2_partial = "https://api.dstserverlist.top/api/details/"
    if res.status_code == requests.codes.ok:
        try:
            server_list = res.json()['List']
        except KeyError:
            print("cant find list in response")
        else:
            for server in server_list:
                if server['Host'] == HOST:
                    row_id = server['RowId']
                    URL2 = URL2_partial + row_id
                    res2 = requests.post(URL2)
                    if res2.status_code == requests.codes.ok:
                        print(res2.json())
                    else:
                        print(res2.content)
    else:
        print(res.content)


if __name__ == "__main__":
    main()
