import asyncio
import sys
from datetime import datetime
from time import sleep

import aiohttp

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
            if time.minute >= 59 or time.minute <= 1:
                PAYLOAD = {'award_id': award_id, 'exchange_num': int(count)}
                resp = await session.post('http://api.live.bilibili.com/activity/v1/NewSpring/redBagExchange', data=PAYLOAD, headers={'Content-Type': 'application/x-www-form-urlencoded'})
                data = await resp.json()
                if data['code'] >= 0:
                    print(data['msg'])
            else:
                await asyncio.sleep(30.0)
            

if __name__ == '__main__':
    tasks = [main() for i in range(20)]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(tasks))
