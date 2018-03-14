from __future__ import print_function

import re
import sys
import asyncio
import requests
from asyncio import Task
from comment_downloader import download_comments


def get_room_id(short_roomid):
    resp = requests.get('https://api.live.bilibili.com/room/v1/Room/room_init?id=' + str(short_roomid))
    data = resp.json()
    return data['data']['room_id']

def extract_short_roomid(url):
    REGEX = re.compile(r'https?://live.bilibili.com/(\d+)')
    match = REGEX.match(url)
    return match.group(1)

async def main():
    comment_task = Task(download_comments(10401, '/dev/null'))
    await asyncio.sleep(5)
    comment_task.cancel()
    print('Ended!')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(0)
    # url = sys.argv[1]
    # room_id = get_room_id(extract_short_roomid(url))
    room_id = 10401
    loop = asyncio.get_event_loop()

    loop.run_until_complete(main())
