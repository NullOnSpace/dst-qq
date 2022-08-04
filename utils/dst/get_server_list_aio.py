import aiohttp
import asyncio


URL_ROOT = "https://api.dstserverlist.top"
param1 = {'name': "旺旺旺", "pageCount":100, 'page':0}
URI_DETAIL = "/api/details/"
HOST = "KU_3RvV9haR"


async def get_server():
    async with aiohttp.ClientSession(URL_ROOT) as session:
        async with session.post("/api/list", params=param1) as res:
            print(res.status)
            r = await res.json()
            return r


async def get_server_detail(rowid):
    async with aiohttp.ClientSession(URL_ROOT) as session:
        async with session.post(URI_DETAIL+rowid) as res:
            print(res.status)
            r = await res.json()
            return r


if __name__ == "__main__":
    asyncio.run(get_server())
