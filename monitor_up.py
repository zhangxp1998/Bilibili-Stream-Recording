from __future__ import print_function

import os
import json
import re
import sys
import time
from datetime import datetime
from multiprocessing import Process
import logging
from logging import debug, info, error
import requests

import google_drive
from comment_downloader import download_comments, write_xml_footer


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
        error('%d, %s', data['code'], data['msg'])
        raise Exception(data['msg'])

def get_stream_info(user_id):
    """
    get uploader's streaming info
    Args:
        user_id: uid of the uploader
    Return:
        A json object with user's streaming info
    """
    resp = requests.get('https://api.vc.bilibili.com/user_ex/v1/user/detail?uid=%s&room[]=live_status' % str(user_id), headers=HEADERS)
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
    return stream_info['room']['live_status'] != 0

def get_stream_download_urls(stream_info):
    """
    get all download urls of the streaming room
    Args:
        stream_info: json object returned by get_stream_info(user_id)
    Returns:
        A json object of all download urls
    """
    global HEADERS
    room_id = stream_info['room']['room_id']
    resp = requests.get('https://api.live.bilibili.com/api/playurl?cid=%s&otype=json&quality=0' % str(room_id), headers=HEADERS)
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
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def download_stream(download_url, stream_save_location):
    """
    Download the URL
    Args:
        download_url: url to download

        stream_save_location: File path to save it, will be passed to open()

        LOG: logger
    """
    global HEADERS
    out_file = open(stream_save_location, 'wb')
    resp = requests.get(download_url, stream=True, headers=HEADERS)
    file_len = 0
    last_log = datetime.now()
    for buf in resp.iter_content(128*1024):
        if buf:
            out_file.write(buf)
            file_len += len(buf)
            delta = datetime.now() - last_log
            
            if delta.total_seconds() > 3:
                info('%s: %s', stream_save_location, sizeof_fmt(file_len))
                last_log = datetime.now()
        else:
            raise Exception("Something's not right...")
    out_file.close()

def get_user_name(uid):
    """
    Query the user's name from bilibili
    Args:
        uid: unique id of the uploader/user
    Returns:
        user's display name in string
    """
    global HEADERS
    resp = requests.get('https://api.live.bilibili.com/user/v1/User/get?uid=%s&platform=pc' % str(uid), headers=HEADERS)
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

def async_upload_delete(file_path):
    p = Process(
        name='Upload ' + file_path,
        target=google_drive.upload_to_google_drive, args=(file_path, True))
    p.start()
    info('PID: %d Start uploading %s', p.pid, file_path)

def main():
    if len(sys.argv) < 2:
        sys.exit(0)
    while True:
        for url in sys.argv[1:]:
            space_id = extract_user_id(url)
            stream_info = get_stream_info(space_id)
            if is_user_streaming(stream_info):
                all_download_urls = get_stream_download_urls(stream_info)
                default_url = all_download_urls['durl'][0]['url']
                debug(default_url)
                save_path = generate_save_path(stream_info)

                video_path = save_path + '.flv'
                p = Process(
                    name=video_path,
                    target=download_stream, args=(default_url, video_path))
                p.start()
                debug('PID: %d NAME: %s', p.pid, p.name)

                comment_path = save_path + '.xml'
                comment_worker = Process(
                    name=comment_path,
                    target=download_comments, args=(stream_info['room']['room_id'], comment_path))
                comment_worker.start()
                debug('PID: %d NAME: %s', comment_worker.pid, comment_worker.name)

                #save stream info and upload it
                meta_info_path = save_path + '.json'
                with open(meta_info_path, 'w') as outfile:
                    json.dump(stream_info, outfile, indent=4, sort_keys=True, ensure_ascii=False)
                async_upload_delete(meta_info_path)

                #wait for stream to end
                p.join()

                #if the stream ends, just kill the comment downloader
                comment_worker.terminate()
                write_xml_footer(comment_path)

                async_upload_delete(comment_path)
                async_upload_delete(video_path)
            else:
                info("%s is not streaming...", get_user_name(space_id))
                time.sleep(3)

if __name__ == '__main__':
    logging.root.setLevel(logging.DEBUG)
    google_drive.google_api_auth()
    main()
