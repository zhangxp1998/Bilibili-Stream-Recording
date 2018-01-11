from __future__ import print_function

import re
import sys

import requests

from comment_downloader import download_comments


def get_room_id(short_roomid):
    resp = requests.get('https://api.live.bilibili.com/room/v1/Room/room_init?id=' + str(short_roomid))
    data = resp.json()
    return data['data']['room_id']

def extract_short_roomid(url):
    REGEX = re.compile(r'https?://live.bilibili.com/(\d+)')
    match = REGEX.match(url)
    return match.group(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(0)
    url = sys.argv[1]
    room_id = get_room_id(extract_short_roomid(url))
    download_comments(room_id, '/dev/null')
