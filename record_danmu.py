import asyncio
from comment_downloader import *
import sys

def main():
    room_id = sys.argv[1]
    comment_path = sys.argv[2]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(download_comments(room_id, comment_path))

if __name__ == '__main__':
    while True:
        try:
            main()
        except KeyboardInterrupt:
            sys.exit(0)
        except:
            pass