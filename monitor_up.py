from __future__ import print_function

import asyncio
import json
import os
import re
import sys
import time
import traceback
from asyncio import Task
from datetime import datetime
from random import random
from threading import Thread

import aiohttp
import async_timeout
import requests

import google_drive
from comment_downloader import download_comments, write_xml_footer


# extract space if of an user(need space url space.bilibili.com/...)
def extract_user_id(url):
    """
        Extract bilibili users' unique id from url to his space
        Args:
            url (str): url to user's space homepage. https://space.bilibili.com/123456
        Returns:
            uid extracted from the url, in string
    """
    REGEX = re.compile(r'https?://.*.bilibili.com/(\d+)')
    match = REGEX.match(url)
    return match.group(1)


def check_json_error(data):
    """
        Check if the json retunred from the server is a success
        Args:
            data (obj): an json object returned from request
    """
    if data['code'] != 0:
        print('%d, %s' % (data['code'], data['msg']))
        raise Exception(data['msg'])


def get_stream_info(user_id, HEADERS={}):
    """
    get uploader's streaming info
    Args:
        user_id: uid of the uploader
    Return:
        A json object with user's streaming info
    """
    resp = requests.get(
        'https://api.vc.bilibili.com/user_ex/v1/user/detail?uid=%s&room[]=live_status' % str(user_id), headers=HEADERS, timeout=5)
    data = resp.json()
    check_json_error(data)
    return data['data']


def is_user_streaming(stream_info):
    """
    check if an user is streaming
    Args:
        stream_info returned by get_stream_info(uid)
    Returns:
        True if the user is streaming, False otherwise
    """
    # 0: offline, 1: streaming, 2: replay
    return stream_info['room']['live_status'] == 1


def get_stream_download_urls(stream_info, HEADERS={}):
    """
    get all download urls of the streaming room
    Args:
        stream_info: json object returned by get_stream_info(user_id)
    Returns:
        A json object of all download urls
    """
    room_id = stream_info['room']['room_id']
    resp = requests.get(
        'https://api.live.bilibili.com/room/v1/Room/playUrl?cid=%s&quality=4&platform=web' % str(room_id), headers=HEADERS, timeout=5)
    return resp.json()


def sizeof_fmt(num, suffix='B'):
    """
    Convert number of byes to human readable form
    Args:
        num: number of bytes
    Returns:
        string in human readable form with suitable unit
    """
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.2f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


async def download_stream(download_url, stream_save_location, HEADERS={}):
    """
    Download the URL
    Args:
        download_url: url to download

        stream_save_location: File path to save it, will be passed to open()

        LOG: logger
    """
    async with aiohttp.ClientSession(headers=HEADERS, conn_timeout=5, read_timeout=None) as session:
        out_file = open(stream_save_location, 'wb')
        try:
            async with session.get(download_url) as resp:
                file_len = 0
                last_log = datetime.now()
                last_size = ''
                # buffer size 128K
                while True:
                    buf = await asyncio.wait_for(resp.content.read(128*1024), timeout=8)
                    if not buf:
                        break
                    out_file.write(buf)
                    out_file.flush()
                    file_len += len(buf)
                    delta = datetime.now() - last_log
                    size = sizeof_fmt(file_len)
                    # print file size every 3 second
                    if delta.total_seconds() > 3 and size != last_size:
                        print('%s: %s' % (stream_save_location, size))
                        last_size = size
                        last_log = datetime.now()
        except:
            tb = traceback.format_exc()
            print(tb)
        out_file.close()


def get_user_name(uid, HEADERS={}):
    """
    Query the user's name from bilibili
    Args:
        uid: unique id of the uploader/user
    Returns:
        user's display name in string
    """
    resp = requests.get(
        'https://api.live.bilibili.com/user/v1/User/get?uid=%s&platform=pc' % str(uid), headers=HEADERS, timeout=5)
    data = resp.json()
    check_json_error(data)
    return data['data']['uname']


def generate_save_path(stream_info):
    '''
    generate a unique path for saving this stream
    Args:
        info: streamming info returned by get_stream_info
    Returns:
        a string of relative path to save the stream
    '''
    uid = str(stream_info['uid'])
    if not os.path.exists(uid):
        os.makedirs(uid)
    return uid + "/" + datetime.now().strftime('%b %d %Y %H:%M:%S')


async def main(url, HEADERS={}):
    # Parse the users's UID
    space_id = extract_user_id(url)
    while True:
        # obtain streamming information about this user
        stream_info = get_stream_info(space_id, HEADERS)
        if is_user_streaming(stream_info):
            # obtain download url of this user's stream
            all_download_urls = get_stream_download_urls(stream_info, HEADERS)
            # randomly choose an URL
            url_count = len(all_download_urls['data']['durl'])
            default_url = all_download_urls['data']['durl'][int(
                random() * url_count)]['url']
            print(default_url)

            # generate a unique save path for downloading files
            save_path = generate_save_path(stream_info)

            # Download the video stream asychronously
            video_path = save_path + '.flv'
            video_task = Task(download_stream(default_url, video_path, HEADERS))
        
            print('Start downloading', video_path)

            # Download the comment stream asychronously
            comment_path = save_path + '.xml'
            comment_task = Task(download_comments(stream_info['room']['room_id'], comment_path, save_path + '.txt'))
            print('Start downloading', comment_path)

            # wait for stream to end
            await video_task
            print('Download thread terminated')
            # # if the stream ends, just kill the comment downloader
            comment_task.cancel()

            if os.path.getsize(video_path) == 0:
                os.remove(video_path)
                os.remove(comment_path)
                print('Failed to download stream')
                continue

            # save stream info and upload it
            meta_info_path = save_path + '.json'
            with open(meta_info_path, 'w') as outfile:
                json.dump(stream_info, outfile, indent=2,
                          sort_keys=True, ensure_ascii=False)
            Thread(target=google_drive.upload_to_google_drive, args=(meta_info_path, True)).start()

            # upload the video and comment file, then delete both files
            Thread(target=google_drive.upload_to_google_drive, args=(comment_path, True)).start()
            Thread(target=google_drive.upload_to_google_drive, args=(video_path, True)).start()
            if os.path.isfile(save_path + '.txt'):
                Thread(target=google_drive.upload_to_google_drive, args=(save_path+'.txt', True)).start()
        else:
            print("%s is not streaming..." % (get_user_name(space_id, HEADERS),))
            await asyncio.sleep(30)

async def handle_url(url, HEADERS):
    while True:
        try:
            await main(url, HEADERS)
        except KeyboardInterrupt:
            break
        except:
            pass

if __name__ == '__main__':
    google_drive.google_api_auth()
    HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7',
        'Accept-Encoding': 'gzip, deflate, br'
    }
    if len(sys.argv) < 2:
        print(sys.argv[0], '')
    tasks = [handle_url(url, HEADERS) for url in sys.argv[1:]]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(tasks))
