import sys

import requests


def purchase_gift(award_id, count, session):
    PAYLOAD = {'award_id': award_id, 'exchange_num': int(count)}
    resp = session.post('http://api.live.bilibili.com/activity/v1/NewSpring/redBagExchange', data=PAYLOAD, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    data = resp.json()
    return data


def main():
    if len(sys.argv) < 4:
        print('Usage: %s award_id count cookie' % (sys.argv[0], ))
        sys.exit(0)
    HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7',
        'Cookie': sys.argv[3],
        'Accept-Encoding': 'gzip, deflate, br'}
    session = requests.Session()
    session.headers = HEADERS
    while True:
        data = purchase_gift(sys.argv[1], sys.argv[2], session)
        print(data['msg'])

if __name__ == '__main__':
    main()
