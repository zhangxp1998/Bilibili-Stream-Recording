from __future__ import print_function

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from threading import Thread

import aiohttp

import google_drive
from comment_downloader import comment_downloader
from monitor_up import get_user_name

APIs = [
        'http://api.live.bilibili.com/gift/v3/smalltv/', 
        'http://api.live.bilibili.com/activity/v1/lottery/',
        'http://api.live.bilibili.com/lottery/v1/Storm/']

LOG_DIR = 'raffle-log'

def reload_cookies(filename, default):
    with open(filename, 'r') as f:
        return [x.strip() for x in f.readlines()]
    return default

def get_uid_from_cookie(cookie):
    p = re.compile(r'DedeUserID=(\d+)')
    m = p.search(cookie)
    return m.group(1)

async def check_raffle_result(headers, log_file, roomId, raffleId, time_left):
    roomId = str(roomId)
    raffleId = str(raffleId)
    await asyncio.sleep(int(time_left)+60)
    async with aiohttp.ClientSession(headers=headers, read_timeout=10, conn_timeout=5) as session:
        async with session.get("http://api.live.bilibili.com/activity/v1/Raffle/notice?roomid=%s&raffleId=%s" % (roomId, raffleId)) as resp:
            data = await resp.json()
            if not os.path.exists(LOG_DIR):
                os.mkdir(LOG_DIR)
            if(data['code'] >= 0):
                if data['data']['gift_name'] == '辣条' or data['data']['gift_num'] <= 0:
                    return
                with open(log_file, 'a') as log_file:
                    print("%s x %d" % (data['data']['gift_name'], data['data']['gift_num']), file=log_file)
            else:
                print(uname, data['msg'])


async def check_raffle(dic):
    roomid = dic.get('real_roomid')
    if roomid is None:
        return
    # print(json.dumps(dic, indent=2, sort_keys=True, ensure_ascii=False))
    roomid = str(roomid)
    print(roomid)
    loop = asyncio.get_event_loop()
    for _, user_data in USER_LIST.items():
        cookie = user_data['cookie']
        uname = user_data['uname']
        log_file = user_data['log_file']
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
                await asyncio.sleep(2);
                for event in data['data']:
                    if event.get('from_user') is None:
                        continue
                    raffleId = event['raffleId']
                    async with session.get(url % (roomid, raffleId)) as resp:
                        raffle_data = await resp.json()
                        print('%s Enter Raffle %s : %s' % (uname, raffleId, raffle_data['msg']))
                        if(raffle_data['code'] >= 0):
                            loop.create_task(check_raffle_result(HEADERS, log_file, roomid, raffleId, event['time']))



            for API_BASE in APIs:
                async with session.get(API_BASE + 'check?roomid=' + roomid) as resp:
                    # resp = await session.get(API_BASE + 'check?roomid=' + roomid)
                    event_list = await resp.json()
                    if event_list['code'] < 0:
                        continue
                    # print(json.dumps(event_list, indent=2, sort_keys=True, ensure_ascii=False))
                    await proc_event_list(event_list, API_BASE + 'join?roomid=%s&raffleId=%s')


def main(USER_LIST):
    room_id = 1017
    danmuji = comment_downloader(room_id, save_path='/dev/null', gift_path='/dev/null', listener_func=check_raffle)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(danmuji.connectServer())
    tasks = [
        asyncio.Task(danmuji.ReceiveMessageLoop()),
        asyncio.Task(danmuji.HeartbeatLoop())
    ]
    loop.run_until_complete(asyncio.wait(tasks))
    danmuji.close()
    for user_data in USER_LIST.values():
        log_file = user_data['log_file']
        if os.path.isfile(log_file):
            Thread(target=google_drive.upload_to_google_drive, args=(log_file, True)).start()
        else:
            print("log file %s not found" % (log_file,))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(sys.argv[0], '<cookie filename>')
        sys.exit(0)
    arr = reload_cookies(sys.argv[1], [])
    USER_LIST = {}
    p = re.compile(r'DedeUserID=(\d+)')
    time_of_day = datetime.now().strftime('%Y-%m-%d %H:%M')
    for cookie in arr:
        m = p.search(cookie)
        uid = m.group(1)
        uname = get_user_name(uid)
        USER_LIST[uid] = {'uname': uname, 'cookie': cookie, 'log_file': '%s/[%s] %s' % (LOG_DIR, uid, time_of_day)}
        print(uname, uid, cookie)

    while True:
        try:
            main(USER_LIST)
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
            sys.exit(0)
        except:
            try:
                for task in asyncio.Task.all_tasks():
                    task.cancel()
            except:
                pass
            pass
