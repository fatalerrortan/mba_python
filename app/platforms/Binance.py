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
import logging 

tracemalloc.start()

class Binance(Platform):

    def __init__(self, ws_url: str, api_host: str, redis: object, api_key: str, secret_key: str):

        self.logger = logging.getLogger("root.{}".format(__name__))
        self._ws_url = ws_url
        self.redis = redis
        self.api_host = api_host
        self._api_key = api_key
        self._secret_key = bytes(secret_key, "utf-8")
        self._headers = {
            "Accept": "*/*",
            'X-MBX-APIKEY': self._api_key
        }

    async def fetch_subscription(self):
        # subscribe  binance market depth to get last bids and asks 
        # response from huobi websocket is a json with cluster of the last bids and asks  
        async with websockets.connect(self._ws_url) as ws: 

            while True:

                if not ws.open:
                    self.logger.warning("............... reconnecting to BINANCE websocket ...............")
                    ws = await websockets.connect(self._ws_url)
                    await ws.send()

                try:
                    raw_respons = await ws.recv()
                    result = json.loads(raw_respons)                                     
                except Exception:
                    self.logger.warning("cannot retrieve trade info from Binance websocket")
                    self.logger.warning(Exception)
                    continue  

                try:
                    max_bid, bid_amount = await self._get_max_bid(result['bids'])
                    if max_bid == None or bid_amount == None: continue
                    min_ask, ask_amount = await self._get_min_ask(result['asks'])
                    if min_ask == None or ask_amount == None: continue
                    json_str = '{"market": "binance","max_bid": '+str(max_bid)+', "bid_amount": '+str(bid_amount)+',"min_ask": '+str(min_ask)+', "ask_amount": '+str(ask_amount)+'}'
                    self.redis.set('binance', json_str) 
                except Exception:
                    self.logger.warning("cannot extract max bid and min sell from retrieved Binance websocket return")
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

    def get_account_balance(self, *currency):

        request_url = self._prepare_request_data("/api/v3/account", {})
        balances = requests.get(request_url, headers=self._headers).json()["balances"]
        result = {}
        
        for balance in balances:
            if len(result) == 2: break
            if balance["asset"].lower() in currency:
                result[balance["asset"].lower()] = balance
        return result

        
    def place_order(self, symbol:str, side: str, type: str, quantity: float, price: float, test_mode=None):
        """
        symbol: currency name e.g. EOSUSDT
        side: trade direction e.g SELL
        type: transaction type
            - LIMIT: trade with limited price
            - MARKET: trade with current market price
            - LIMIT_MAKER: ???
            - STOP_LOSS: trade with current market price if lower than a stop price 
            - STOP_LOSS_LIMIT: trade with a specified price if lower than a stop price 
            - TAKE_PROFIT: trade with current market price if higher than a stop price 
            - TAKE_PROFIT_LIMIT: trade with specified price if higher than a stop price
        timeInForce：IOC - Immediate or Cancel 
                     GTC - Good till cancel
                     FOK - Fill or Kill
        """
        params = {
           "symbol": symbol.upper(),
           "side": side.upper(),
           "type": type.upper(),
           "timeInForce": "IOC",
           "quantity": quantity,
           "price": price,
           # "stopPrice": stop_price,
           "newOrderRespType": "RESULT"
        }
        endpoint = "/api/v3/order/test" if test_mode == True else "/api/v3/order"
        request_url = self._prepare_request_data(endpoint, params)
        # self.logger.debug(request_url)
        try:
            balances = requests.post(request_url, headers=self._headers).json()
            if balances["orderId"]: 
                return balances
            else: return None
        except Exception:
            self.logger.critical("cannot place Binance trade order")
            self.logger.critical(Exception)
            return None
        
        return balances

    def _prepare_request_data(self, uri: str, params: dict):
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