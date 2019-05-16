from platforms.Platform import Platform
import asyncio
import websockets
import gzip
import json
import tracemalloc
import datetime

tracemalloc.start()

class Huobi(Platform):

    def __init__(self, ws_url: str, redis: object):
        self._ws_url = ws_url
        self.redis = redis

    async def fetch_subscription(self, sub: str):
        # subscribe  huobi market depth to get last bids and asks 
        # response from huobi websocket is a json with cluster of the last bids and asks  
        async with websockets.connect(self._ws_url) as ws: 
            await ws.send(sub)  
            while True:
                raw_respons = await ws.recv()
                try:
                    result = gzip.decompress(raw_respons).decode('utf-8')
                except Exception as e:
                    print(__file__+f' line 25: {e}')                        
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
                        self.redis.set('huobi', str(result))                      
                    except Exception as e:
                        print(__file__+f' line 38: {e}')     

    def _get_max_bid(self, bids: list) -> tuple:
        # get the highst bid price of the given bids cluster
        max_bid = 0
        bid_amount = 0
        for bid, amount in bids:
            current_bid = float(bid)
            if current_bid > max_bid:
                max_bid = current_bid
                bid_amount = float(amount)
        return (max_bid, bid_amount)

    def _get_min_ask(self, asks: list) -> tuple:
        # get the lowst ask price of the given asks cluster
        min_ask = 0
        ask_amount = 0
        for ask, amount in asks:
            current_ask = float(ask)
            if (current_ask < min_ask) or (min_ask == 0):
                min_ask = current_ask
                ask_amount = float(amount)
        return (min_ask, ask_amount)