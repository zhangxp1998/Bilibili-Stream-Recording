import asyncio
from comment_downloader import *
import sys

def main():
    room_id = sys.argv[1]
    while True:
        prefix =  'gift-log'
        if not os.path.exists(prefix):
            os.makedirs(prefix)
        comment_path = prefix + '/' + '[' + room_id + '] ' + datetime.now().strftime('%Y-%m-%d %H:%M') + '.xml'
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait_for(download_comments(room_id, comment_path), timeout=60*60*24))
        Thread(target=google_drive.upload_to_google_drive, args=(comment_path, True)).start()


if __name__ == '__main__':
    while True:
        try:
            main()
        except KeyboardInterrupt:
            sys.exit(0)
        except:
            pass