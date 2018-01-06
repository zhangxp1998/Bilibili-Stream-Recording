from __future__ import print_function
from comment_downloader import download_comments

from monitor_up import *
import requests

def get_room_id(short_roomid):
    resp = requests.get('https://api.live.bilibili.com/room/v1/Room/room_init?id=' + str(short_roomid))
    data = resp.json()
    return data['data']['room_id']

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(0)
    url = sys.argv[1]
    REGEX = re.compile(r'https?://live.bilibili.com/(\d+)')
    match = REGEX.match(url)
    room_id = get_room_id(match.group(1))
    download_comments(room_id, '/dev/null')
