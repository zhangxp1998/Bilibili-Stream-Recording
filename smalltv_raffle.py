from __future__ import print_function

import asyncio
import json
import sys
import re
import aiohttp
from monitor_up import get_user_name
from comment_downloader import comment_downloader
APIs = [
            'http://api.live.bilibili.com/gift/v2/smalltv/', 
            'http://api.live.bilibili.com/activity/v1/Raffle/',
            'http://api.live.bilibili.com/lottery/v1/Storm/']

def reload_cookies(filename, default):
    with open(filename, 'r') as f:
        return [x.strip() for x in f.readlines()]
    return default

async def check_raffle_result(headers, roomId, raffleId, time_left):
    roomId = str(roomId)
    raffleId = str(raffleId)
    await asyncio.sleep(int(time_left)+60)
    async with aiohttp.ClientSession(headers=headers, read_timeout=10, conn_timeout=5) as session:
        async with session.get("http://api.live.bilibili.com/activity/v1/Raffle/notice?roomid=%s&raffleId=%s" % (roomId, raffleId)) as resp:
            data = await resp.json()
            if(data['code'] >= 0):
                print("%s x %d" % (data['data']['gift_name'], data['data']['gift_num']))
            else:
                print(data['msg'])


async def check_raffle(dic):
    roomid = dic.get('real_roomid')
    if roomid is None:
        return
    # print(json.dumps(dic, indent=2, sort_keys=True, ensure_ascii=False))
    roomid = str(roomid)
    print(roomid)
    loop = asyncio.get_event_loop()
    for uname, cookie in COOKIES.items():
        HEADERS = {
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': dic['url'],
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7',
            'Accept': 'application/json, text/plain, */*'
        }
        async with aiohttp.ClientSession(headers=HEADERS, read_timeout=10, conn_timeout=5) as session:
            async def proc_event_list(data, url):
                if data['code'] < 0:
                    return
                for event in data['data']:
                    if event.get('from_user') is None:
                        continue
                    raffleId = event['raffleId']
                    async with session.get(url % (roomid, raffleId)) as resp:
                        data = await resp.json()
                        print('%s Enter Raffle %s : %s' % (uname, raffleId, data['msg']))
                        if(data['code'] >= 0):
                            loop.create_task(check_raffle_result(HEADERS, roomid, raffleId, event['time']))



            for API_BASE in APIs:
                async with session.get(API_BASE + 'check?roomid=' + roomid) as resp:
                    # resp = await session.get(API_BASE + 'check?roomid=' + roomid)
                    event_list = await resp.json()
                    if event_list['code'] < 0:
                        continue
                    # print(json.dumps(event_list, indent=2, sort_keys=True, ensure_ascii=False))
                    await proc_event_list(event_list, API_BASE + 'join?roomid=%s&raffleId=%s')


def main():
    room_id = 1017
    danmuji = comment_downloader(room_id, save_path='/dev/null', gift_path='/dev/null', listener_func=check_raffle)
    
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
    arr = reload_cookies(sys.argv[1], [])
    COOKIES = {}
    p = re.compile(r'DedeUserID=(\d+)')
    for cookie in arr:
        m = p.search(cookie)
        uname = get_user_name(m.group(1))
        COOKIES[uname] = cookie
        print(uname, m.group(1), cookie)

    while True:
        try:
            main()
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
            sys.exit(0)
        except:
            pass
