from __future__ import print_function

import datetime
import os
import re
import sys
import time
import json
from multiprocessing import Process

import requests

import google_drive

REGEX = re.compile(r'https?://.*.bilibili.com/(\d+)')
HEADERS = {
    'User-Agent': 'Safari/537.36',
    'Accept-Encoding':'gzip, deflate, br'
}

#extract space if of an user(need space url space.bilibili.com/...)
def extract_user_id(url):
    """
        Extract bilibili users' unique id from url to his space
        Args:
            url (str): url to user's space homepage. https://space.bilibili.com/123456
    """
    global REGEX
    match = REGEX.match(url)
    return match.group(1)

def check_json_error(data):
    """
        Check if the json retunred from the server is a success
        Args:
            data (obj): an json object
    """
    if data['code'] != 0:
        print(data['code'], file=sys.stderr)
        raise Exception(data['msg'])

def get_stream_info(user_id):
    resp = requests.get('https://api.vc.bilibili.com/user_ex/v1/user/detail?uid=%s&room[]=live_status' % str(user_id), headers=HEADERS)
    data = resp.json()
    check_json_error(data)
    return resp.json()['data']

def is_user_streaming(stream_info):
    return stream_info['room']['live_status'] != 0

def get_stream_download_urls(stream_info):
    global HEADERS
    room_id = stream_info['room']['room_id']
    resp = requests.get('https://api.live.bilibili.com/api/playurl?cid=%s&otype=json&quality=0' % str(room_id), headers=HEADERS)
    return resp.json()

def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def merge_comments(history, new):
    if len(history) == 0:
        history.extend(new)
        return history
    i = 0
    last = history[len(history)-1]['timeline']
    while i < len(new) and new[i]['timeline'] <= last:
        i+=1
    if i >= len(new):
        return history
    history.extend(new[i:])
    return history

def write_ass_headers(save_path):
    with open(save_path, 'w') as out:
        out.write('[Script Info]\n')
        out.write('Title: bilibili ASS Danmaku Downloader\n')
        out.write('ScriptType: v4.00+\n')
        out.write('Collisions: Normal')
        out.write('PlayResX: 560\n')
        out.write('PlayResY: 420\n')
        out.write('Timer: 10.0000\n')
        out.write('[V4+ Styles]\n')
        out.write('Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n')
        out.write('Style: Fix,Ariel,25,&H66FFFFFF,&H66FFFFFF,&H66000000,&H66000000,1,0,0,0,100,100,0,0,1,2,0,2,20,20,2,0\n')
        out.write('Style: R2L,Ariel,25,&H66FFFFFF,&H66FFFFFF,&H66000000,&H66000000,1,0,0,0,100,100,0,0,1,2,0,2,20,20,2,0\n')
        out.write('\n')
        out.write('[Events]\n')
        out.write('Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')


def append_more_history(save_path, history):
    with open(save_path, 'w') as out:
        for item in history:
            out.write('Dialog:0,\n')


def download_comments(room_id, save_path, start_time):
    if save_path.endswith('.flv'):
        save_path = save_path[0:-3] + 'ass'
    if not save_path.endswith('ass'):
        save_path += 'ass'

    write_ass_headers(save_path)
    request_data = {'roomid': room_id}
    resp = requests.post('http://live.bilibili.com/ajax/msg', data=request_data)
    data = resp.json()
    history = []

    while data['code'] == 0:
        comments = data['data']['room']
        merge_comments(history, comments)
        print(history)
        if len(history) > 10:
            append_more_history(save_path, history)
            history = []

        time.sleep(1)
        resp = requests.post('http://live.bilibili.com/ajax/msg', data=request_data)
        data = resp.json()
    return data

def download_stream(download_url, save_path):
    global HEADERS
    if not save_path.endswith('.flv'):
        save_path += '.flv'
    out_file = open(save_path, 'wb')
    resp = requests.get(download_url, stream=True, headers=HEADERS)
    sum = 0
    for buf in resp.iter_content(128*1024):
        if buf:
            out_file.write(buf)
            sum += len(buf)
            print(sizeof_fmt(sum))
        else:
            raise Exception("Something's not right...")
    out_file.close()

def get_user_name(uid):
    global HEADERS
    resp = requests.get('https://api.live.bilibili.com/user/v1/User/get?uid=%s&platform=pc' % str(uid), headers=HEADERS)
    data = resp.json()
    check_json_error(data)
    return data['data']['uname']

def generate_save_path(info):
    '''
    info: streamming info returned by get_stream_info
    '''
    uid = str(info['uid'])
    uname = get_user_name(uid)
    if not os.path.exists(uid):
        os.makedirs(uid)
    return uid + "/" + datetime.datetime.now().strftime('%b %d %Y %H:%M.flv')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(0)
    while True:
        for url in sys.argv[1:]:
            space_id = extract_user_id(url)
            info = get_stream_info(space_id)
            if is_user_streaming(info):
                all_download_urls = get_stream_download_urls(info)
                default_url = all_download_urls['durl'][0]['url']
                save_path = generate_save_path(info)
                print(save_path, default_url)
                p = Process(target=download_stream, args=(default_url, save_path))
                p.start()
                p.join()
                # download_stream(default_url, save_path)
                print('Start uploading ' + save_path)
                p = Process(target=google_drive.upload_to_google_drive, args=(save_path,))
                p.start()
            else:
                print(get_user_name(space_id) + " is not streaming...")
                time.sleep(3)
