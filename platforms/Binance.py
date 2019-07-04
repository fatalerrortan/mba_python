from platforms.Platform import Platform
import asyncio
import websockets
import gzip
import json
import tracemalloc
import time
import traceback
import requests
import hashlib
import hmac
import base64

tracemalloc.start()

class Binance(Platform):

    def __init__(self, ws_url: str, api_host: str, redis: object, api_key: str, secret_key: str):
        self._ws_url = ws_url
        self.redis = redis
        self.api_host = api_host
        self._api_key = api_key
        self._secret_key = bytes(secret_key, "utf-8")

    async def fetch_subscription(self):
        # subscribe  binance market depth to get last bids and asks 
        # response from huobi websocket is a json with cluster of the last bids and asks  
        async with websockets.connect(self._ws_url) as ws: 

            while True:

                if not ws.open:
                    print('............... reconnecting to BINANCE websocket ...............')
                    ws = await websockets.connect(self._ws_url)
                    await ws.send()

                try:
                    raw_respons = await ws.recv()
                    result = json.loads(raw_respons)                                     
                except Exception as e:
                    print(traceback.format_exc())
                    continue  
                try:
                    max_bid, bid_amount = await self._get_max_bid(result['bids'])
                    if max_bid == None or bid_amount == None: continue
                    min_ask, ask_amount = await self._get_min_ask(result['asks'])
                    if min_ask == None or ask_amount == None: continue
                    # json_str = '{"max_bid": {}, "bid_amount": {}, "min_ask": {},ç "ask_amount": {}}'.format(max_bid, bid_amount, min_ask, ask_amount)
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

    def get_account_balance(self, *currency):
        headers = {
            "Accept": "*/*",
            'X-MBX-APIKEY': self._api_key
        }
        request_url = self._prepare_request_data("/api/v3/account")
        try:
            result = requests.get(request_url, headers=headers).json()
        except Exception:
            print(Exception)
            return None
        print(result)

    def _prepare_request_data(self, uri: str, **params):
        request_params_dict = {
            "timestamp": int(time.time()*1000)
        } 

        if params:
            request_params_dict = {**request_params_dict, **params}      
        
        request_params = ""
        for key in sorted(request_params_dict.keys()):
            request_params += "{}={}&".format(key,request_params_dict[key])

        signature = self._get_hmacSHA256_sigature(request_params[:-1])       
        request_url = "{}{}?{}signature={}".format(self.api_host, uri, request_params, signature)

        return request_url

    def _get_hmacSHA256_sigature(self, request_params: str):
        hash = hmac.new(self._secret_key, bytes(request_params, "utf-8"), hashlib.sha256).hexdigest()

        return hash