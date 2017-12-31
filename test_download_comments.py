from __future__ import print_function

from datetime import datetime

from dateutil import parser
from dateutil.tz import gettz
from pytz import timezone

from monitor_up import *

if __name__ == '__main__':
    tzinfos = {None: gettz('Asia/Harbin')}
    comment_time = parser.parse('2017-12-30 15:42:00', tzinfos=tzinfos)
    print(comment_time)
    print(datetime.datetime.now(gettz('Asia/Harbin')) - comment_time)
    
    # print(comment_time.format('%Y %B %d %H:%M:%S'))
    # comment_time = comment_time - timedelta(hours=12)
    # download_comments('5269', 'test.ass', datetime.datetime.now())
