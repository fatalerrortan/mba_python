from platforms.Platform import Platform
import asyncio
import websockets
import gzip
import json
import tracemalloc
import datetime
import traceback

tracemalloc.start()

class Huobi(Platform):

    def __init__(self, ws_url: str, redis: object):
        self._ws_url = ws_url
        self.redis = redis
        self.sub = None

    async def fetch_subscription(self, sub: str):
        # subscribe  huobi market depth to get last bids and asks 
        # response from huobi websocket is a json with cluster of the last bids and asks  
        self.sub = sub
        async with websockets.connect(self._ws_url) as ws: 
            await ws.send(sub)  
            while True:

                if not ws.open:
                    print('............... reconnecting to HUOBI websocket ...............')
                    ws = await websockets.connect(self._ws_url)
                    await ws.send(sub)
                    
                try:
                    raw_respons = await ws.recv()
                    result = gzip.decompress(raw_respons).decode('utf-8')
                    
                except Exception:
                    print(traceback.format_exc())
                    continue                             
                if result[2:6] == 'ping':
                    ping = str(json.loads(result).get('ping'))
                    pong = '{"pong":'+ping+'}'
                    await ws.send(pong)
                else:
                    try:
                        result = json.loads(result).get('tick')
                        if not result: continue
                        # result['ts'] = datetime.datetime.fromtimestamp(int(result['ts']/1000)).strftime('%Y-%m-%d %H:%M:%S')
                        max_bid, bid_amount = await self._get_max_bid(result['bids'])
                        if max_bid == None or bid_amount == None: continue
                        min_ask, ask_amount = await self._get_min_ask(result['asks'])
                        if min_ask == None or ask_amount == None: continue
                        # json_str = '{"max_bid": {}, "bid_amount": {}, "min_ask": {}, "ask_amount": {}}'.format(max_bid, bid_amount, min_ask, ask_amount)
                        json_str = '{"market": "huobi","max_bid": '+str(max_bid)+', "bid_amount": '+str(bid_amount)+',"min_ask": '+str(min_ask)+', "ask_amount": '+str(ask_amount)+'}'                        
                        self.redis.set('huobi', json_str)                      
                    except Exception:
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