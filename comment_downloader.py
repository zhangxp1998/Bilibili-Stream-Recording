from __future__ import print_function

import asyncio
import json
import xml.dom.minidom
from datetime import datetime
from struct import *

import aiohttp
import requests


def download_comments(room_id, save_path):
    danmuji = comment_downloader(room_id, save_path)
    tasks = [
        danmuji.connectServer(),
        danmuji.HeartbeatLoop()
    ]
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(asyncio.wait(tasks))
    except KeyboardInterrupt:
        print('Keyboard Interrupt received...')
        danmuji.close()

        for task in asyncio.Task.all_tasks():
            task.cancel()


def write_xml_header(save_path):
    with open(save_path, 'wb') as out_file:
        out_file.write(b'<?xml version="1.0" encoding="UTF-8"?><i><chatserver>chat.bilibili.com</chatserver><chatid>0</chatid><mission>0</mission><maxlimit>0</maxlimit><source>k-v</source>\n')


def append_comment(save_path, comment_json):
    with open(save_path, 'a') as out_file:
        # content of the comment
        text = comment_json['info'][1]
        # name of the user who sent this comment
        user = comment_json['info'][2][1]
        # meta info
        payload = str(comment_json['info'][0])[1:-1]
        out_file.write('<d p="' + payload + '">' +
                       user + ': ' + text + '</d>\n')


def write_xml_footer(save_path):
    with open(save_path, 'ab') as out_file:
        out_file.write(b'</i>\n')

class comment_downloader():
    def __init__(self, room_id, save_path='test.xml', listener_func=None):
        self._CIDInfoUrl = 'http://live.bilibili.com/api/player?id=cid:'
        self._roomId = 0
        self._ChatPort = 788
        self._protocolversion = 1
        self._reader = 0
        self._writer = 0
        self.connected = False
        self._UserCount = 0
        self._ChatHost = 'livecmt-1.bilibili.com'
        self._roomId = room_id
        self._roomId = int(self._roomId)
        self._save_path = save_path
        self._start_time = datetime.now()
        self.TURN_WELCOME = True
        self.TURN_GIFT = True
        self.callback = listener_func
        self._session = aiohttp.ClientSession()

    async def connectServer(self):
        # self._roomId = get_true_roomid(self._roomId)
        print('room_id: ' + str(self._roomId))
        self._ChatHost, self._ChatPort = await self.get_chat_info()

        reader, writer = await asyncio.open_connection(self._ChatHost, self._ChatPort)
        self._reader = reader
        self._writer = writer
        self._start_time = datetime.now()
        write_xml_header(self._save_path)
        print('connecting...')
        if await self.SendJoinChannel(self._roomId):
            self.connected = True
            print('Connected!')
            await self.ReceiveMessageLoop()

    async def get_chat_info(self):
        # room_id is the true room id obtained from
        # https://api.live.bilibili.com/room/v1/Room/room_init?id=
        async with self._session.get('http://live.bilibili.com/api/player?id=cid:' + str(self._roomId), headers={
            'Accept': '*/*',
            'User-Agent': 'Safari/537.36',
            'Accept-Encoding': 'gzip, deflate, br'}) as resp:
            text = await resp.text()
            dom = xml.dom.minidom.parseString('<root>' + text + '</root>')
            root = dom.documentElement
            server = root.getElementsByTagName('dm_server')
            port = root.getElementsByTagName('dm_port')
            return (server[0].firstChild.data, port[0].firstChild.data)

    def close(self):
        self.connected = False
        self._writer.close()
        write_xml_footer(self._save_path)

    async def HeartbeatLoop(self):
        while not self.connected:
            await asyncio.sleep(0.5)

        while self.connected:
            await self.SendSocketData(0, 16, self._protocolversion, 2, 1, "[object object]")
            await asyncio.sleep(30)

    async def SendJoinChannel(self, channelId):
        self._uid = 0
        body = '{"roomid":%s, "uid":%s, "protover": %d}' % (
            channelId, self._uid, self._protocolversion)
        await self.SendSocketData(0, 16, self._protocolversion, 7, 1, body)
        return True

    async def SendSocketData(self, packetlength, headrlen, ver, action, param, body):
        bytearr = body.encode('utf-8')
        if packetlength == 0:
            packetlength = len(bytearr) + headrlen
        sendbytes = pack('!IHHII', packetlength, headrlen, ver, action, param)
        if len(bytearr) != 0:
            sendbytes = sendbytes + bytearr
        self._writer.write(sendbytes)
        await self._writer.drain()

    async def ReceiveMessageLoop(self):
        while self.connected:
            tmp = await self._reader.read(4)
            expr, = unpack('!I', tmp)
            tmp = await self._reader.read(2)
            tmp = await self._reader.read(2)
            tmp = await self._reader.read(4)
            num, = unpack('!I', tmp)
            tmp = await self._reader.read(4)
            num2 = expr - 16

            if num2 != 0:
                num -= 1
                if num == 0 or num == 1 or num == 2:
                    tmp = await self._reader.read(4)
                    num3, = unpack('!I', tmp)
                    print('房间人数为 ' + str(num3))
                    self._UserCount = num3
                    continue
                elif num == 3 or num == 4:
                    tmp = await self._reader.read(num2)
                    # strbytes, = unpack('!s', tmp)
                    try:  # 为什么还会出现 utf-8 decode error??????
                        messages = tmp.decode('utf-8')
                    except:
                        continue
                    self.parseDanMu(messages)
                    continue
                elif num == 5 or num == 6 or num == 7:
                    tmp = await self._reader.read(num2)
                    continue
                else:
                    if num != 16:
                        tmp = await self._reader.read(num2)
                    else:
                        continue

    def parseDanMu(self, messages):
        try:
            dic = json.loads(messages)
        except:  # 有些情况会 jsondecode 失败，未细究，可能平台导致
            return
        if self.callback is not None:
            return self.callback(dic)

        cmd = dic['cmd']
        if cmd == 'LIVE':
            print('直播开始。。。')
            return
        elif cmd == 'PREPARING':
            print('房主准备中。。。')
            return
        elif cmd == 'DANMU_MSG':
            commentText = dic['info'][1]
            commentUser = dic['info'][2][1]
            isAdmin = dic['info'][2][2] == '1'
            isVIP = dic['info'][2][3] == '1'
            if isAdmin:
                commentUser = '管理员 ' + commentUser
            if isVIP:
                commentUser = 'VIP ' + commentUser
            try:
                delta = datetime.now() - self._start_time
                dic['info'][0][0] = delta.total_seconds()
                #print('%s: %s' % (commentUser, commentText))
                append_comment(self._save_path, dic)
            except:
                pass
            return
        elif cmd == 'SEND_GIFT' and self.TURN_GIFT:
            GiftName = dic['data']['giftName']
            GiftUser = dic['data']['uname']
            Giftrcost = dic['data']['rcost']
            GiftNum = dic['data']['num']
            try:
                print('%s 送出了 %d 个 %s' % (GiftUser, GiftNum, GiftName))
            except:
                pass
            return
        elif cmd == 'WELCOME' and self.TURN_WELCOME:
            commentUser = dic['data']['uname']
            try:
                print('欢迎 %s 进入房间。。。。' % (commentUser, ))
            except:
                pass
            return
        else:
            print(json.dumps(dic, indent=4, sort_keys=True, ensure_ascii=False))
        return
