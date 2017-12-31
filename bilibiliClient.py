from __future__ import print_function

import asyncio
import json
import random
import xml.dom.minidom
from struct import *

import requests


def get_true_roomid(short_room_id):
    resp = requests.get('https://api.live.bilibili.com/room/v1/Room/room_init?id=' + str(short_room_id))
    data = resp.json()
    return data['data']['room_id']

def get_chat_info(room_id):
    resp = requests.get('http://live.bilibili.com/api/player?id=cid:' + str(room_id), headers={'Accept': '*/*'})
    text = resp.text
    print(text)
    dom = xml.dom.minidom.parseString('<root>' + text + '</root>')
    root = dom.documentElement
    server = root.getElementsByTagName('dm_server')
    port = root.getElementsByTagName('dm_port')
    return (server[0].firstChild.data, port[0].firstChild.data)

class bilibiliClient():
    def __init__(self, room_id):
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
        self.TURN_WELCOME = True
        self.TURN_GIFT = True



    async def connectServer(self):
        self._roomId = get_true_roomid(self._roomId)
        print('room_id: ' + str(self._roomId))
        self._ChatHost, self._ChatPort = get_chat_info(self._roomId)
        
        reader, writer = await asyncio.open_connection(self._ChatHost, self._ChatPort)
        self._reader = reader
        self._writer = writer
        print ('链接弹幕中。。。。。')
        if (await self.SendJoinChannel(self._roomId) == True):
            self.connected = True
            print ('进入房间成功。。。。。')
            print ('链接弹幕成功。。。。。')
            await self.ReceiveMessageLoop()

    async def HeartbeatLoop(self):
        while not self.connected:
            await asyncio.sleep(0.5)

        while self.connected:
            await self.SendSocketData(0, 16, self._protocolversion, 2, 1, "")
            await asyncio.sleep(30)


    async def SendJoinChannel(self, channelId):
        self._uid = 0
        body = '{"roomid":%s,"uid":%s}' % (channelId, self._uid)
        await self.SendSocketData(0, 16, self._protocolversion, 7, 1, body)
        return True


    async def SendSocketData(self, packetlength, magic, ver, action, param, body):
        bytearr = body.encode('utf-8')
        if packetlength == 0:
            packetlength = len(bytearr) + 16
        sendbytes = pack('!IHHII', packetlength, magic, ver, action, param)
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
                    print('房间人数为 %s' % num3)
                    self._UserCount = num3
                    continue
                elif num == 3 or num == 4:
                    tmp = await self._reader.read(num2)
                    # strbytes, = unpack('!s', tmp)
                    try: # 为什么还会出现 utf-8 decode error??????
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
        except: # 有些情况会 jsondecode 失败，未细究，可能平台导致
            return
        cmd = dic['cmd']
        if cmd == 'LIVE':
            print('直播开始。。。')
            return
        if cmd == 'PREPARING':
            print('房主准备中。。。')
            return
        if cmd == 'DANMU_MSG':
            commentText = dic['info'][1]
            commentUser = dic['info'][2][1]
            isAdmin = dic['info'][2][2] == '1'
            isVIP = dic['info'][2][3] == '1'
            if isAdmin:
                commentUser = '管理员 ' + commentUser
            if isVIP:
                commentUser = 'VIP ' + commentUser
            try:
                print(commentUser + ': ' + commentText)
            except:
                pass
            return
        if cmd == 'SEND_GIFT' and self.TURN_GIFT:
            GiftName = dic['data']['giftName']
            GiftUser = dic['data']['uname']
            Giftrcost = dic['data']['rcost']
            GiftNum = dic['data']['num']
            try:
                print(GiftUser + ' 送出了 ' + str(GiftNum) + ' 个 ' + GiftName)
            except:
                pass
            return
        if cmd == 'WELCOME' and self.TURN_WELCOME:
            commentUser = dic['data']['uname']
            try:
                print ('欢迎 ' + commentUser + ' 进入房间。。。。')
            except:
                pass
            return
        return
