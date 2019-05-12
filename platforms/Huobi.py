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
        self._ws_url = ws_url

    def fetch_subscription(self, sub: str):
        try:
            async def request_subscription(sub: str):
                async with websockets.connect(self._ws_url) as ws: 
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
                                result['bids'] = self._get_max_bid(result['bids'])
                                result['asks'] = self._get_min_ask(result['asks'])                       
                            except Exception as e:
                                print(e)     
                            print(result) 
                            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        except ConnectionError as e:
            print(e)
        # asyncio.get_event_loop().run_until_complete(
        #     request_subscription(sub)
        # )
        asyncio.run(request_subscription(sub))

    def _get_max_bid(self, bids: list):
        max_bid = 0
        bid_amount = 0
        for bid, amount in bids:
            current_bid = float(bid)
            if current_bid > max_bid:
                max_bid = current_bid
                bid_amount = float(amount)
        return (max_bid, bid_amount)

    def _get_min_ask(self, asks: list):
        min_ask = 0
        ask_amount = 0
        for ask, amount in asks:
            current_ask = float(ask)
            if (current_ask < min_ask) or (min_ask == 0):
                min_ask = current_ask
                ask_amount = float(amount)
        return (min_ask, ask_amount)