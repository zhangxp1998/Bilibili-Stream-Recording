import asyncio
import sys
from datetime import datetime
from time import sleep

import aiohttp
from aiohttp import client_exceptions

EXCHANGE_URL = 'http://api.live.bilibili.com/activity/v1/NewSpring/redBagExchange'

async def main():
    if len(sys.argv) < 4:
        print('Usage: %s award_id count cookie' % (sys.argv[0], ))
        sys.exit(0)
    HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7',
        'Cookie': sys.argv[3],
        'Accept-Encoding': 'gzip, deflate, br'}
    award_id = sys.argv[1]
    count = int(sys.argv[2])

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        while True:
            time = datetime.now()
            if (time.minute >= 59 and time.second >= 45) or (time.minute <= 0 and time.second <= 15):
                PAYLOAD = {'award_id': award_id, 'exchange_num': int(count)}
                resp = await session.post(EXCHANGE_URL, data=PAYLOAD)
                try:
                    data = await resp.json()
                    print(data['msg'])
                except client_exceptions.ContentTypeError:
                    print(await resp.text())
            else:
                target = datetime(time.year, time.month, time.day, time.hour, 59, 45, 0)
                delta = target - datetime.now()
                await asyncio.sleep(delta.total_seconds())
            

if __name__ == '__main__':
    tasks = [main() for i in range(2)]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(tasks))
