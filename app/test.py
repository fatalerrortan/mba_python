from platforms.Huobi import Huobi
from platforms.Binance import Binance
from Core import Core
import asyncio
import redis
import configparser
from prettytable import PrettyTable
from analyser.Freq_Analyser import Freq_Analyser
import signal
import logging
import datetime
import sys
import os
import traceback

currency_code = "eth"
exec_mode = "production"
rule_file = "testing_0.5.json"

logger = logging.getLogger("root")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s / %(levelname)s / %(name)s / %(message)s")

sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
sh.setFormatter(formatter)

dt = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

if not os.path.isdir("logs"):
        os.makedirs("logs", os.umask(0))

fh = logging.FileHandler("logs/{}_{}.log".format(dt, currency_code))
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)

logger.addHandler(sh)
logger.addHandler(fh)

config = configparser.ConfigParser()

config.read('etc/{}.ini'.format(currency_code))
# config.read('../etc/{}.ini'.format(currency_code))

CURRENCY_PAIR = currency_code + 'usdt'

HUOBI_WS_URL = config['HUOBI']['ws_url']
HUOBI_TOPIC_MARKET_DEPTH = config['HUOBI']['stream'].replace('$currency_pair', CURRENCY_PAIR)
HUOBI_API_HOST = config['HUOBI']['api_host']
HUOBI_API_KEY = config['HUOBI']['access_key']
HUOBI_SECRET_KEY = config['HUOBI']['secret_key']
#simulation params
HUOBI_CURRENCY_AMOUNT = config['HUOBI']['simulated_currency_amount']
HUOBI_USDT_AMOUNT = config['HUOBI']['simulated_usdt_amount']

BINANCE_WS_URL = config['BINANCE']['ws_url']
BINANCE_STREAM = config['BINANCE']['stream'].replace('$currency_pair', CURRENCY_PAIR)
BINANCE_API_HOST = config['BINANCE']['api_host']
BINANCE_API_KEY = config['BINANCE']['access_key']
BINANCE_SECRET_KEY = config['BINANCE']['secret_key']
#simulation params
BINANCE_CURRENCY_AMOUNT = config['BINANCE']['simulated_currency_amount']
BINANCE_USDT_AMOUNT = config['BINANCE']['simulated_usdt_amount']

REDIS_URL = config['DATABASE']['redis_url']
REDIS_PORT = config['DATABASE']['redis_port']
REDIS_INDEX = config['DATABASE']['redis_index']

if __name__ == '__main__':
        
        logger.info(">>> TanMba is running <<<")

        try:
                redis = redis.Redis(host=REDIS_URL, port=REDIS_PORT, db=REDIS_INDEX)
                redis.set('currency_code', currency_code)
                redis.set('trade_rule_file', rule_file)
        except Exception as e:
                logger.critical(getattr(e, 'message', repr(e)))
                logger.critical(traceback.format_exc())
                raise 
        binance_coroutine = Binance(BINANCE_WS_URL+BINANCE_STREAM, BINANCE_API_HOST, redis, BINANCE_API_KEY, BINANCE_SECRET_KEY)
        huobi_coroutine = Huobi(HUOBI_WS_URL, HUOBI_API_HOST, redis, HUOBI_API_KEY, HUOBI_SECRET_KEY)     
        freq_analyser = Freq_Analyser(currency_code)
        core_coroutine = Core(redis, currency_code, freq_analyser, huobi_coroutine, binance_coroutine) 


        # result = core_coroutine.lot_size_validate("0.19129999999999999782")
        # print(result)
        result = huobi_coroutine.get_trade_fee("eth")
        print(result)
        # result1 = huobi_coroutine.get_account_balance("eth", "usdt")
        # print(result1)
        # {'eos': {'currency': 'eos', 'type': 'trade', 'balance': '0.1994'}, 'usdt': {'currency': 'usdt', 'type': 'trade', 'balance': '9.72044542'}}
        
        # result2 = huobi_coroutine.place_order(0.1, 250, "ethusdt", "sell-limit")
        # print(result2)
        # order_id = result2["data"]
        
        # {'status': 'ok', 'data': '70913970151'}
        # 70913970151

        # result3 = huobi_coroutine.get_account_balance("eos", "usdt")
        # print(result3)
        # {'eos': {'currency': 'eos', 'type': 'trade', 'balance': '0'}, 'usdt': {'currency': 'usdt', 'type': 'trade', 'balance': '9.72044542'}}

        # result4 = huobi_coroutine.get_order_detail(73389829586)
        # print(result4)


        # result5 = huobi_coroutine.cancel_order(order_id)
        # print(result5)
        # {'status': 'error', 'err-code': 'method-not-allowed', 'err-msg': "Request method 'GET' not supported", 'data': None}
        # {'status': 'ok', 'data': '70913970151'}

        # result5 = huobi_coroutine.fetch_subscription("eosusdt", "step0")
        # print(result5)

# !!!!!!!!!!!!!!!! binance !!!!!!!!!!!!!!!!!
        # balance = binance_coroutine.get_account_balance("eos", "usdt")
        # print(balance)

        # result1 = binance_coroutine.place_order("eosusdt", "sell", "limit", 2.99, 3.618, "GTC")
        # print(result1)
        # order_id = result1["orderId"]
        # print(order_id)

        # balance = binance_coroutine.get_account_balance("eos", "usdt")
        # print(balance)

        # result2 = binance_coroutine.get_order_detail("eosusdt", 520220791)
        # print(result2)

        # result3 = binance_coroutine.cancel_order("eosusdt", 520220791)
        # print(result3)

        # result4 = binance_coroutine.get_order_detail("eosusdt", 520220791)
        # print(result4)





        



