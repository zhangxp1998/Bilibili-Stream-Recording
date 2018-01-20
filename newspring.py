import json
import sys

import requests


def purchase_gift(award_id):
    HEADERS = {
        'Cookie': sys.argv[1],
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip, deflate, br'}
    PAYLOAD = {'award_id': award_id, 'exchange_num': 50}
    resp = requests.post('http://api.live.bilibili.com/activity/v1/NewSpring/redBagExchange', data=PAYLOAD)
    data = resp.json()
    return data


if __name__ == '__main__':
    while True:
        data = purchase_gift('gift-109')
        print(data['msg'])
