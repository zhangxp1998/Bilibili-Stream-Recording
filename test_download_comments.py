from __future__ import print_function

from datetime import datetime, timedelta

from dateutil import parser
from pytz import timezone

from monitor_up import *

if __name__ == '__main__':
    comment_time = parser.parse('2017-12-25 11:50:05')
    # comment_time = comment_time - timedelta(hours=12)
    comment_time.replace(tzinfo=timezone('Asia/China'))
    print(comment_time)
    download_comments('5269', 'test.ass', datetime.datetime.now())
