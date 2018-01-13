from __future__ import print_function

import asyncio
import sys
import json
import requests

from comment_downloader import comment_downloader
from test_download_comments import extract_short_roomid, get_room_id


def check_raffle(dic):
    cmd = dic['cmd']
    if cmd != 'SYS_MSG':
        return
    # print(json.dumps(dic, indent=2, sort_keys=True, ensure_ascii=False))
    roomid = dic.get('real_roomid')
    print(roomid)
    if roomid is None:
        return
    HEADERS = {
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': dic['url'],
        'Cookies': sys.argv[2],
        'User-Agent': 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7',
        'Accept': 'application/json, text/plain, */*'
    }
    resp = requests.get(
        'http://api.live.bilibili.com/gift/v2/smalltv/check?roomid=' + str(roomid), headers=HEADERS)
    data = resp.json()
    # print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
    for event in data['data']:
        resp = requests.get(
            'http://api.live.bilibili.com/gift/v2/smalltv/join?roomid=%s&raffleId=%s' % (roomid, event['raffleId']), headers={'Referer': dic['url'], 'Cookie': sys.argv[2]})
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
