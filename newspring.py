import sys

import requests


def purchase_gift(award_id):
    HEADERS = {
        'Cookie': sys.argv[3],
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip, deflate, br'}
    PAYLOAD = {'award_id': award_id, 'exchange_num': int(sys.argv[2])}
    resp = requests.post('http://api.live.bilibili.com/activity/v1/NewSpring/redBagExchange', data=PAYLOAD, headers=HEADERS)
    data = resp.json()
    return data


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: %s award_id count cookie' % (sys.argv[0], ))
        sys.exit(0)
    while True:
        data = purchase_gift(sys.argv[1])
        print(data['msg'])
