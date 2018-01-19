from __future__ import print_function

import asyncio
import json
import sys

import requests

from comment_downloader import comment_downloader
from test_download_comments import extract_short_roomid, get_room_id


def check_raffle(dic):
    cmd = dic['cmd']
    roomid = dic.get('real_roomid')
    if roomid is None:
        return
    # print(json.dumps(dic, indent=2, sort_keys=True, ensure_ascii=False))
    roomid = str(roomid)
    print(roomid)
    HEADERS = {
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': dic['url'],
        'Cookie': sys.argv[2],
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7',
        'Accept': 'application/json, text/plain, */*'
    }
    def proc_event_list(data, url):
        if data['code'] < 0:
            return
        for event in data['data']:
            if event.get('from_user') is None:
                continue
            resp = requests.get(
                url % (roomid, event['raffleId']), headers=HEADERS)
            data = resp.json()
            # print(json.dumps(dic, indent=2, sort_keys=True, ensure_ascii=False))
            print('Enter Raffle %d: %s' % (event['raffleId'], data['msg']))
    
    # APIs = [
    #     'http://api.live.bilibili.com/gift/v2/smalltv/', 
    #     'http://api.live.bilibili.com/activity/v1/Raffle/',
    #     'http://api.live.bilibili.com/lottery/v1/Storm/']
    # for API_BASE in APIs:
    #     resp = requests.get(API_BASE + 'check?roomid=' + roomid, headers=HEADERS)
    #     event_lit = resp.json()
    #     if event_lit['code'] < 0:
    #         continue
    #     print(json.dumps(event_lit, indent=2, sort_keys=True, ensure_ascii=False))
    #     for event in event_lit['data']:
    #         if event.get('from_user') is None:
    #             continue
    #         resp = requests.get(
    #             API_BASE + 'join?roomid=%sraffleId=%s' % (roomid, event['raffleId']), headers=HEADERS)
    #         data = resp.json()
    #         print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
    #         print('Enter Raffle %d: %s' % (event['raffleId'], data['msg']))
    
    resp = requests.get(
        'http://api.live.bilibili.com/gift/v2/smalltv/check?roomid=' + roomid, headers=HEADERS)
    data = resp.json()
    # print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
    proc_event_list(data, 'http://api.live.bilibili.com/gift/v2/smalltv/join?roomid=%s&raffleId=%s')
    
    resp = requests.get('http://api.live.bilibili.com/activity/v1/Raffle/check?roomid=' + roomid, headers=HEADERS)
    data = resp.json()
    # print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
    proc_event_list(data, 'http://api.live.bilibili.com/activity/v1/Raffle/join?roomid=%s&raffleId=%s')

    resp = requests.get('http://api.live.bilibili.com/lottery/v1/Storm/check?roomid=' + roomid)
    data = resp.json()
    proc_event_list(data, 'http://api.live.bilibili.com/lottery/v1/Storm/join?roomid=%sraffleId=%s')


def main():
    url = sys.argv[1]
    room_id = get_room_id(extract_short_roomid(url))
    danmuji = comment_downloader(room_id, '/dev/null', check_raffle)
    tasks = [
        danmuji.connectServer(),
        danmuji.HeartbeatLoop()
    ]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(tasks))

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(0)
    while True:
        try:
            main()
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
            sys.exit(0)
        except:
            pass
