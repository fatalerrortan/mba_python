from platforms.Platform import Platform
import asyncio
import websockets
import gzip
import json
import tracemalloc
import datetime
import traceback
import urllib.parse
import requests
from datetime import datetime
import hashlib
import hmac
import base64
import time
import logging

tracemalloc.start()

class Huobi(Platform):
 
    def __init__(self, ws_url: str, api_host: str, redis: object, api_key: str, secret_key: str):
        
        self.logger = logging.getLogger("root.{}".format(__name__))
        self._ws_url = ws_url
        self.redis = redis
        self.sub = None
        self.api_host = api_host
        self._api_key = api_key
        self._secret_key = bytes(secret_key, "utf-8")
        self._account_id = None

    async def fetch_subscription(self, sub: str):
        # subscribe  huobi market depth to get last bids and asks 
        # response from huobi websocket is a json with cluster of the last bids and asks  
        self.sub = sub
        async with websockets.connect(self._ws_url) as ws: 
            await ws.send(sub)  
            while True:

                if not ws.open:
                    self.logger.warning("............... reconnecting to BINANCE websocket ...............")                           
                    ws = await websockets.connect(self._ws_url)
                    await ws.send(sub)
                    
                try:
                    raw_respons = await ws.recv()
                    result = gzip.decompress(raw_respons).decode('utf-8')
                    
                except Exception:
                    self.logger.warning(Exception)
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
                        self.logger.warning(Exception)
                        continue    

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

    def get_account_info(self):
        
        while True:
            request_url = self._prepare_request_data("GET", "/v1/account/accounts")
            result = requests.get(request_url).json()
            if not result["status"] == "error":
                self._account_id = result['data'][0]["id"]
                return result

    def get_account_balance(self, *currency):

        if not self._account_id:
            self.get_account_info()

        currency_list = list(currency)
        result = {}

        while True:
            request_url = self._prepare_request_data("GET", "/v1/account/accounts/{}/balance".format(self._account_id))
            raw_result = requests.get(request_url).json()
            if not raw_result["status"] == "error":
                balances = raw_result["data"]["list"]
                for balance in balances:
                    if len(result) == 2: break
                    if (balance["currency"] in currency_list) and (balance["type"] == "trade"):
                        result[balance["currency"]] = balance
      
                return result

    def place_order(self, amount: float, price: float, symbol: str, trade_type: str):
        """
            trade_type: using buy as example for explanation
                1. buy(sell)-market: A market order is an order to trade a stock at the current market price.
                    - in this case the argument "price" is optional
                
                2. buy(sell)-limit: A buy limit order is an order to purchase an asset at or below a specified price

                3. buy(sell)-ioc: An Immediate Or Cancel (IOC) order requires all or part of the order to be executed immediately, 
                and any unfilled parts of the order are canceled.

                4. buy(sell)-limit-maker: an order will be placed only when the offering bid price is lower than current lowest ask price.
        """
        if not self._account_id:
            self.get_account_info()

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        post_data = {
            "account-id": str(self._account_id),
            "amount": str(amount),
            "price": str(price),
            "source": "api",
            "symbol": str(symbol),
            "type": str(trade_type)
        }

        post_data = json.dumps(post_data)
    
        while True:
            request_url = self._prepare_request_data("POST", "/v1/order/orders/place")
            result = requests.post(request_url, post_data, headers=headers).json()
            if result["status"] == "error" and result["err-code"] == "api-signature-not-valid":
                continue
            return result
            
    def _prepare_request_data(self, post_method: str, uri: str, **params):
        request_params_dict = {
            "AccessKeyId": self._api_key,
            "SignatureMethod": "HmacSHA256",
            "SignatureVersion": 2,
            "Timestamp": urllib.parse.quote(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'))
        }

        if params:
            request_params_dict = {**request_params_dict, **params}

        request_params = ""
        for key in sorted(request_params_dict.keys()):
            request_params += "{}={}&".format(key,request_params_dict[key])

        request_message = "{}\n{}\n{}\n{}".format(post_method, self.api_host, uri, request_params)[:-1]
        signature = self._get_hmacSHA256_sigature(request_message)
        request_params += "Signature={}".format(signature)

        request_url = "https://{}{}?{}".format(self.api_host, uri, request_params)

        return request_url

    def _get_hmacSHA256_sigature(self, request_message: str):
        hash = hmac.new(self._secret_key, bytes(request_message, "utf-8"), hashlib.sha256).digest()
        base64_hash = base64.b64encode(hash)

        return base64_hash.decode("utf-8")