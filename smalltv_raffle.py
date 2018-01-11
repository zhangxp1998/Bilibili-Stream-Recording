from __future__ import print_function

import asyncio
import sys

import requests

from comment_downloader import comment_downloader
from test_download_comments import extract_short_roomid, get_room_id


def check_raffle(dic):
    roomid = dic.get('real_roomid')
    if roomid is None:
        return
    HEADERS = {
        'User-Agent': 'Safari/537.36',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': dic['url'],
        'Cookies': sys.argv[2]
    }
    resp = requests.get(
        'http://api.live.bilibili.com/activity/v1/Raffle/check?roomid=' + str(roomid), headers=HEADERS)
    data = resp.json()
    if data['code'] != 0:
        print('Check Raffle', data['msg'])
    for event in data['data']:
        resp = requests.get(
            'http://api.live.bilibili.com/gift/v2/smalltv/join?roomid=%s&raffleId=%s' % (roomid, event['raffleId']))
        data = resp.json()
        print('Enter Raffle %d: %s' % (event['raffleId'], data['msg']))
    return


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(0)
    url = sys.argv[1]
    room_id = get_room_id(extract_short_roomid(url))
    danmuji = comment_downloader(room_id, '/dev/null', check_raffle)
    tasks = [
        danmuji.connectServer(),
        danmuji.HeartbeatLoop()
    ]
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(asyncio.wait(tasks))
    except KeyboardInterrupt:
        print('Keyboard Interrupt received...')
        danmuji.close()

        for task in asyncio.Task.all_tasks():
            task.cancel()
