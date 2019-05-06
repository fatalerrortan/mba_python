from platforms.Platform import Platform
import asyncio
import websockets
import gzip
import json
import tracemalloc
import datetime

tracemalloc.start()

class Huobi(Platform):

    def __init__(self, ws_url=None):
        self.ws_url = ws_url

    def fetch_subscription_test(self, sub=None):
        try:
            async def request_subscription(sub):
                async with websockets.connect(self.ws_url) as ws: 
                    await ws.send(sub)  
                    while True:
                        raw_respons = await ws.recv()
                        try:
                            result = gzip.decompress(raw_respons).decode('utf-8')
                        except:
                            print('the response of huobi server cannot be decompressed')                        
                        if result[2:6] == 'ping':
                            ping = str(json.loads(result).get('ping'))
                            pong = '{"pong":'+ping+'}'
                            await ws.send(pong)
                        else:
                            try:
                                result = json.loads(result)
                                if result.get('ch', None) == None:
                                    continue
                            except:
                                print("the response of huobi cannot be parsed in json")
                            trade_market = result.get('ch', 'not defined')
                            try:
                                trade_data = result.get('tick').get('data')
                            except:
                                print('the response of huobi doesn\'t contain trade information')
                            for trade in trade_data:
                                prepared_trade_data = {}
                                prepared_trade_data['trade_id'] = trade.get('id')
                                prepared_trade_data['trade_datetime'] = datetime.datetime.fromtimestamp(int(trade.get('ts')/1000)).strftime('%Y-%m-%d %H:%M:%S')
                                prepared_trade_data['trade_amount'] = trade.get('amount')
                                prepared_trade_data['trade_price'] = trade.get('price')
                                prepared_trade_data['trade_direction'] = trade.get('direction')

                                # yield prepared_trade_data
                                print(trade_data+"\r\n------------------------------------------\r\n")
                                

                                # print('\r\n---------------------\r\nmarket: {} \r\ntrade id: {}\r\ndate: {}\r\namount: {}\r\nprice: {}\r\ndirection: {}\r\n----------------------'
                                #     .format(trade_market, trade_id, trade_datetime, trade_amount, trade_price, trade_direction))
        except ConnectionError as e:
            print(e)
        asyncio.get_event_loop().run_until_complete(
            request_subscription(sub)
        )

    def fetch_subscription(self, sub=None):
        try:
            async def request_subscription(sub):
                async with websockets.connect(self.ws_url) as ws: 
                    await ws.send(sub)  
                    while True:
                        raw_respons = await ws.recv()
                        try:
                            result = gzip.decompress(raw_respons).decode('utf-8')
                        except:
                            print('the response of huobi server cannot be decompressed')                        
                        if result[2:6] == 'ping':
                            ping = str(json.loads(result).get('ping'))
                            pong = '{"pong":'+ping+'}'
                            await ws.send(pong)
                        else:
                            try:
                                result = json.loads(result).get('tick')
                                result['ts'] = datetime.datetime.fromtimestamp(int(result['ts']/1000)).strftime('%Y-%m-%d %H:%M:%S')                        
                            except:
                                print("the response of huobi cannot be parsed in json")     
                            print(result) 
        except ConnectionError as e:
            print(e)
        asyncio.get_event_loop().run_until_complete(
            request_subscription(sub)
        )

    def get_current_bid(self):
        pass

    def get_current_ask(self):
        pass