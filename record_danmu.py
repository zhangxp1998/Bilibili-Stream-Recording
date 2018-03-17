import asyncio
import os
import sys
from datetime import datetime
from threading import Thread

import google_drive
from comment_downloader import download_comments

INTERVAL = 60

async def main(room_id):
    while True:
        prefix =  'gift-log'
        if not os.path.exists(prefix):
            os.makedirs(prefix)
        path = prefix + '/' + '[' + room_id + '] ' + datetime.now().strftime('%Y-%m-%d %H:%M')
        comment_path = path + '.xml'
        gift_path = path + '.txt'
        try:
            await asyncio.wait_for(download_comments(room_id, comment_path, gift_path), timeout=INTERVAL)
        except asyncio.TimeoutError:
            pass
        Thread(target=google_drive.upload_to_google_drive, args=(comment_path, True)).start()
        if os.path.isfile(gift_path):
            Thread(target=google_drive.upload_to_google_drive, args=(gift_path, True)).start()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    while True:
        try:
            tasks = [main(room_id) for room_id in sys.argv[1:]]
            loop.run_until_complete(asyncio.wait(tasks))
        except KeyboardInterrupt:
            sys.exit(0)
        except:
            pass
