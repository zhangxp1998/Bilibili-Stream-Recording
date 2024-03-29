from __future__ import print_function

import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from multiprocessing import Pool, Process
import google_drive
import urllib3
import requests
import socket
from functools import lru_cache


HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7',
    'Accept-Encoding': 'gzip, deflate, br'
}

# extract space if of an user(need space url space.bilibili.com/...)

BAD_URLS = set()


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


def retry(times, exceptions):
  """
  Retry Decorator
  Retries the wrapped function/method `times` times if the exceptions listed
  in ``exceptions`` are thrown
  :param times: The number of times to repeat the wrapped function/method
  :type times: Int
  :param Exceptions: Lists of exceptions that trigger a retry attempt
  :type Exceptions: Tuple of Exceptions
  """
  def decorator(func):
    def newfn(*args, **kwargs):
      attempt = 0
      while attempt < times:
        try:
          return func(*args, **kwargs)
        except exceptions as e:
          print(
              'Exception {} thrown when attempting to run {}, attempt {} of {}' .format(
                  e, func, attempt, times)
          )
          attempt += 1
      return func(*args, **kwargs)
    return newfn
  return decorator


@retry(3, (urllib3.exceptions.MaxRetryError, socket.gaierror, urllib3.exceptions.NewConnectionError, requests.exceptions.ConnectionError))
def get_stream_info(user_id):
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
  resp = requests.get('https://live.bilibili.com/' +
                      str(room_id), headers=HEADERS)
  if '__NEPTUNE_IS_MY_WAIFU__={' in resp.text:
    data = resp.text[resp.text.index('__NEPTUNE_IS_MY_WAIFU__={'):]
    data = data[len('__NEPTUNE_IS_MY_WAIFU__='):]
    if '</script>' in data:
      data = data[:data.index('</script>')]
    data = json.loads(data)
    codecs = data['roomInitRes']['data']['playurl_info']['playurl']['stream'][0]['format'][0]['codec']

    def url_from_codec(codec):
      return codec['url_info'][0]['host'] + codec['base_url'] + codec['url_info'][0]['extra']
    for codec in codecs:
      url = url_from_codec(codec)
      if url not in BAD_URLS:
        return url
    return url_from_codec(codecs[0])


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


def download_stream(download_url, stream_save_location, stream_info):
  """
  Download the URL
  Args:
    download_url: url to download

    stream_save_location: File path to save it, will be passed to open()

    LOG: logger
  """
  global HEADERS
  headers = {**HEADERS, 'Referer': "https://live.bilibili.com/" +
             str(stream_info["room"]["room_id"])}
  resp = requests.get(download_url, stream=True, headers=headers, timeout=5)
  file_len = 0
  last_log = datetime.now()
  last_size = ''
  try:
    with open(stream_save_location, 'wb') as out_file:
      # buffer size 128K
      for buf in resp.iter_content(128 * 1024):
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
    BAD_URLS.add(download_url)
    while len(BAD_URLS) > 10:
      BAD_URLS.pop()
    raise


@lru_cache
def get_user_name(uid):
  """
  Query the user's name from bilibili
  Args:
    uid: unique id of the uploader/user
  Returns:
    user's display name in string
  """
  global HEADERS
  resp = requests.get(
      'https://api.bilibili.com/x/space/acc/info?mid=%s' % str(uid), headers=HEADERS, timeout=5)
  data = resp.json()
  check_json_error(data)
  return data['data']['name']


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


def async_upload_delete(file_path, pool):
  pool.apply_async(
      func=google_drive.upload_to_google_drive,
      args=(file_path, True),
      callback=print,
      error_callback=lambda e: print("%s upload error: %s" % (file_path, e)))
  print('Start uploading %s' % (file_path, ))


def main():
  if len(sys.argv) < 2:
    sys.exit(0)
  if len(sys.argv) == 3:
    logging.basicConfig(filename=sys.argv[2])
  # Parse the users's UID
  url = sys.argv[1]
  space_id = extract_user_id(url)
  pool = Pool(processes=2)
  while True:
    # obtain streamming information about this user
    try:
      stream_info = get_stream_info(space_id)
    except requests.exceptions.RequestException:
      logging.exception("Got exception when trying to get_stream_info")
      time.sleep(5)
      continue
    if is_user_streaming(stream_info):
      # obtain download url of this user's stream
      default_url = get_stream_download_urls(stream_info)
      print(default_url)

      # generate a unique save path for downloading files
      save_path = generate_save_path(stream_info)

      # Download the video stream asychronously
      video_path = save_path + '.flv'
      p = Process(
          name=video_path,
          target=download_stream, args=(default_url, video_path, stream_info))
      p.start()
      print('PID: %d NAME: %s' % (p.pid, p.name))

      # Download the comment stream asychronously

      # save stream info and upload it
      meta_info_path = save_path + '.json'
      with open(meta_info_path, 'w') as outfile:
        json.dump(stream_info, outfile, indent=2,
                  sort_keys=True, ensure_ascii=False)
      async_upload_delete(meta_info_path, pool)

      # wait for stream to end
      p.join()

      # if the stream ends, just kill the comment downloader

      if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
        os.remove(video_path)
        # os.remove(comment_path)
        print('Failed to download stream')
        continue

      # upload the video and comment file, then delete both files
      # async_upload_delete(comment_path, pool)
      async_upload_delete(video_path, pool)
    else:
      print("%s is not streaming..." % (get_user_name(space_id),))
      time.sleep(30)


if __name__ == '__main__':
  google_drive.google_api_auth()
  while True:
    try:
      main()
    except KeyboardInterrupt:
      break
