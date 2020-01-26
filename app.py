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

config = configparser.ConfigParser()
config.read('./config_dev.ini')

EXEC_MODE = config['MODE']['mode']

CURRENCY_PAIR = config['MODE']['currency_code'] + 'usdt'

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

logger = logging.getLogger("root")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s / %(levelname)s / %(name)s / %(message)s")

sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
sh.setFormatter(formatter)

fh = logging.FileHandler("logs/core.log")
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)

logger.addHandler(sh)
logger.addHandler(fh)

if __name__ == '__main__':
        
        logger.info(">>> TanMba is running <<<")

        try:
                redis = redis.Redis(host=REDIS_URL, port=REDIS_PORT, db=REDIS_INDEX)
        except Exception:
                logger.critical(Exception)
                raise Exception
        
        binance_coroutine = Binance(BINANCE_WS_URL+BINANCE_STREAM, BINANCE_API_HOST, redis, BINANCE_API_KEY, BINANCE_SECRET_KEY)
        huobi_coroutine = Huobi(HUOBI_WS_URL, HUOBI_API_HOST, redis, HUOBI_API_KEY, HUOBI_SECRET_KEY)    
        freq_analyser = Freq_Analyser(config['MODE']['currency_code'])
        core_coroutine = Core(redis, config['MODE']['currency_code'], freq_analyser) 

        if EXEC_MODE == 'simulation':

                redis.set('exec_mode', 'simulation')
                redis.set('huobi_currency_amount', HUOBI_CURRENCY_AMOUNT)  
                redis.set('huobi_usdt_amount', HUOBI_USDT_AMOUNT)
                redis.set('binance_currency_amount', BINANCE_CURRENCY_AMOUNT)  
                redis.set('binance_usdt_amount', BINANCE_USDT_AMOUNT)
        else:
                redis.set('exec_mode', 'production')
                
                huobi_account_info = huobi_coroutine.get_account_balance(config['MODE']['currency_code'], "usdt")
                HUOBI_CURRENCY_AMOUNT = huobi_account_info['eos']['balance']
                HUOBI_USDT_AMOUNT = huobi_account_info['usdt']['balance']        

                binance_account_info = binance_coroutine.get_account_balance(config['MODE']['currency_code'], "usdt")
                BINANCE_CURRENCY_AMOUNT = binance_account_info['eos']['free']
                BINANCE_USDT_AMOUNT = binance_account_info['usdt']['free']

                redis.set('huobi_currency_amount', HUOBI_CURRENCY_AMOUNT)  
                redis.set('huobi_usdt_amount', HUOBI_USDT_AMOUNT)
                redis.set('binance_currency_amount', BINANCE_CURRENCY_AMOUNT)  
                redis.set('binance_usdt_amount', BINANCE_USDT_AMOUNT)

        table = PrettyTable()
        table.field_names = ["Platforms", config['MODE']['currency_code'].upper(), "USDT"]

        table.add_row(["HUOBI", float(redis.get('huobi_currency_amount')), float(redis.get('huobi_usdt_amount'))])
        table.add_row(["BINANCE", float(redis.get('binance_currency_amount')), float(redis.get('binance_usdt_amount'))])

        logger.info("{}{}".format("\r\n", table))

        signal.signal(signal.SIGINT, freq_analyser.write_to_csv)

        asyncio.get_event_loop().run_until_complete(asyncio.gather(
                huobi_coroutine.fetch_subscription(sub=HUOBI_TOPIC_MARKET_DEPTH),
                binance_coroutine.fetch_subscription(),
                core_coroutine.bricks_checking()
                ))

        # .................. testing ..........................................       

        # test = huobi_coroutine.get_account_balance("eos", "usdt")
        # test1 = huobi_coroutine.place_order(0.1, 6.11, "eosusdt", "sell-ioc")
        # print(test1)
        # test2 = huobi_coroutine.get_account_balance("eos", "usdt")
        # print(test2)
        
        # on working!!!

        # logger.info(binance_coroutine.get_account_balance("eos","usdt"))
        # logger.debug(binance_coroutine.place_order("eosusdt", "buy", "LIMIT", 1, 3.7, test_mode=True))
        # logger.info(binance_coroutine.get_account_balance("eos","usdt"))
        
        
        
   
        