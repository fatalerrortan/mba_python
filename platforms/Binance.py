from platforms.Platform import Platform
import asyncio
import websockets
import gzip
import json
import tracemalloc
import datetime
import traceback

tracemalloc.start()

class Binance(Platform):

    def __init__(self, ws_url: str, redis: object):
        self._ws_url = ws_url
        self.redis = redis

    async def fetch_subscription(self):
        # subscribe  binance market depth to get last bids and asks 
        # response from huobi websocket is a json with cluster of the last bids and asks  
        async with websockets.connect(self._ws_url) as ws: 

            while True:
                raw_respons = await ws.recv()
                try:
                    result = json.loads(raw_respons)                                     
                except Exception as e:
                    print(traceback.format_exc())
                try:
                    max_bid, bid_amount = await self._get_max_bid(result['bids'])
                    if max_bid == None or bid_amount == None: continue
                    min_ask, ask_amount = await self._get_min_ask(result['asks'])
                    if min_ask == None or ask_amount == None: continue
                    # json_str = '{"max_bid": {}, "bid_amount": {}, "min_ask": {}, "ask_amount": {}}'.format(max_bid, bid_amount, min_ask, ask_amount)
                    json_str = '{"market": "binance","max_bid": '+str(max_bid)+', "bid_amount": '+str(bid_amount)+',"min_ask": '+str(min_ask)+', "ask_amount": '+str(ask_amount)+'}'
                    self.redis.set('binance', json_str) 
                except Exception as e:
                    print(traceback.format_exc())                            

    async def _get_max_bid(self, bids: list):
        # get the highst bid price of the given bids cluster
        max_bid = 0
        bid_amount = 0
        for bid, amount in bids:
            current_bid = float(bid)
            if current_bid > max_bid:
                max_bid = current_bid
                bid_amount = float(amount)
        return max_bid, bid_amount

    async def _get_min_ask(self, asks: list):
        # get the lowst ask price of the given asks cluster
        min_ask = 0
        ask_amount = 0
        for ask, amount in asks:
            current_ask = float(ask)
            if (current_ask < min_ask) or (min_ask == 0):
                min_ask = current_ask
                ask_amount = float(amount)
        return min_ask, ask_amount