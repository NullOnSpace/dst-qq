"""Check if dst update beta or formal
"""

import aiohttp
from bs4 import BeautifulSoup as BS
import requests


class TooManyRequests(Exception):
    pass


URL = "https://forums.kleientertainment.com/game-updates/dst/"

def fetch_page():
    """Fetch page and return the response object"""         
    while True:
        res = requests.get(URL)
        fail_count = 0
        if res.status_code == requests.codes.ok:
            return res
        else:
            fail_count += 1
            if fail_count == 5:
                raise TooManyRequests("fetch page 6 times")


async def aio_fetch_page():
    fail_count = 0
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.get(URL) as res:
                if res.status == 200:
                    return await res.text()
                else:
                    fail_count += 1
                    if fail_count == 5:
                        raise TooManyRequests("fetch page 6 times")



def analyze_page(raw_html):
    """Analyze page and
     return the patch list in tuple
     (patch No.(int),"Test" or "Release", release date, hot fix(false) or release(true), order No.)"""
    soup = BS(raw_html, "html.parser")
    patch_tags = soup.find_all(name="li", attrs={"class": "cCmsRecord_row"})
    patch_list = []
    for t in patch_tags:
        patch_no = str(list(t.a.h3.strings)[0]).strip()
        t_or_r_tag = t.a.h3.span
        if t_or_r_tag:
            test_or_release = str(t.a.h3.span.string)
        else:
            test_or_release = 'both'
        release_date = str(t.a.div.string).strip('\n\t.')
        is_hotfix = t.find(name="i", attrs={"class": "fa-warning"}) and True
        rowid = t.attrs["data-rowid"]
        patch_list.append((patch_no, test_or_release, release_date, is_hotfix, rowid))
    return patch_list


def get_latest_version(test=False):
    try:
        r = fetch_page()
    except TooManyRequests:
        return "Network Error"
    else:
        pl = analyze_page(r.content)
    pattern = "{patch_no:6} {tor:8} {date:17}"
    meta = 'Test' if test else 'Release'
    m = max(
        filter(lambda x: x[1]==meta or x[1]=='both', pl), 
        key=lambda x: int(x[0]),
    )
    return pattern.format(patch_no=m[0], tor=m[1], date=m[2][9:])


async def aio_get_latest_version(test=False):
    try:
        content = await aio_fetch_page()
    except TooManyRequests:
        return "Network Error"
    else:
        pl = analyze_page(content)
    pattern = "{patch_no:6} {tor:8} {date:17}"
    meta = 'Test' if test else 'Release'
    m = max(
        filter(lambda x: x[1]==meta or x[1]=='both', pl), 
        key=lambda x: int(x[0])
    )
    return pattern.format(patch_no=m[0], tor=m[1], date=m[2][9:])


def print_metas(patch_list):
    pattern = "{patch_no:6} {tor:8} {date:17} {hotfix:5} {rowid:5}"
    for patch in patch_list:
        print(pattern.format(
            patch_no=patch[0], tor=patch[1], date=patch[2],
            hotfix=str(patch[3]),
            rowid=patch[4],
        ))

def main():
    """Fetch page and print patch list"""
    import pprint

    r = fetch_page()
    pl = analyze_page(r.content)
    print_metas(pl)

if __name__ == "__main__":
    import asyncio
    r = asyncio.run(aio_get_latest_version())
    print(r)
