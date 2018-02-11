from __future__ import print_function

import asyncio
import json
import sys

import aiohttp

from comment_downloader import comment_downloader
from test_download_comments import extract_short_roomid, get_room_id

COOKIES = []

def reload_cookies(filename, default):
    with open(filename, 'r') as f:
        return [x.strip() for x in f.readlines()]
    return default


async def check_raffle(dic):
    roomid = dic.get('real_roomid')
    if roomid is None:
        return
    # print(json.dumps(dic, indent=2, sort_keys=True, ensure_ascii=False))
    roomid = str(roomid)
    print(roomid)
    for cookie in COOKIES:
        HEADERS = {
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': dic['url'],
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7',
            'Accept': 'application/json, text/plain, */*'
        }
        async with aiohttp.ClientSession(headers=HEADERS, read_timeout=5, conn_timeout=5) as session:
            async def proc_event_list(data, url):
                if data['code'] < 0:
                    return
                for event in data['data']:
                    if event.get('from_user') is None:
                        continue
                    async with session.get(url % (roomid, event['raffleId'])) as resp:
                        data = await resp.json()
                        print('Enter Raffle %d: %s' % (event['raffleId'], data['msg']))
            
            APIs = [
                'http://api.live.bilibili.com/gift/v2/smalltv/', 
                'http://api.live.bilibili.com/activity/v1/Raffle/',
                'http://api.live.bilibili.com/lottery/v1/Storm/']
            for API_BASE in APIs:
                resp = session.get(API_BASE + 'check?roomid=' + roomid)
                event_list = resp.json()
                if event_list['code'] < 0:
                    continue
                # print(json.dumps(event_list, indent=2, sort_keys=True, ensure_ascii=False))
                asyncio.get_event_loop().create_task(proc_event_list(event_list, API_BASE + 'join?roomid=%s&raffleId=%s'))


def main():
    room_id = 66688
    danmuji = comment_downloader(room_id, '/dev/null', check_raffle)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(danmuji.connectServer())
    tasks = [
        danmuji.ReceiveMessageLoop(),
        danmuji.HeartbeatLoop()
    ]
    loop.run_until_complete(asyncio.wait(tasks))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(sys.argv[0], '<cookie filename>')
        sys.exit(0)
    COOKIES = reload_cookies(sys.argv[1], [])
    while True:
        try:
            main()
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
            sys.exit(0)
        except:
            pass
