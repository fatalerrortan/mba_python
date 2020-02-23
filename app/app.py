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

currency_code = sys.argv[1]
exec_mode = sys.argv[2]

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

# config.read('etc/{}.ini'.format(currency_code))
config.read('../etc/{}.ini'.format(currency_code))

TRADE_RULE_FILE = config['RULE']['rule_file']
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
                redis.set('trade_rule_file', TRADE_RULE_FILE)
        except Exception as e:
                logger.critical(getattr(e, 'message', repr(e)))
                logger.critical(traceback.format_exc())
                raise 
        
        binance_coroutine = Binance(BINANCE_WS_URL+BINANCE_STREAM, BINANCE_API_HOST, redis, BINANCE_API_KEY, BINANCE_SECRET_KEY)
        huobi_coroutine = Huobi(HUOBI_WS_URL, HUOBI_API_HOST, redis, HUOBI_API_KEY, HUOBI_SECRET_KEY)    
        freq_analyser = Freq_Analyser(currency_code)
        core_coroutine = Core(redis, currency_code, freq_analyser) 

        if exec_mode == 'simulation':

                redis.set('exec_mode', 'simulation')

                redis.set('huobi_currency_amount', HUOBI_CURRENCY_AMOUNT)  
                redis.set('huobi_usdt_amount', HUOBI_USDT_AMOUNT)

                redis.set('binance_currency_amount', BINANCE_CURRENCY_AMOUNT)  
                redis.set('binance_usdt_amount', BINANCE_USDT_AMOUNT)

        else:
                redis.set('exec_mode', 'production')
                
                try:
                        huobi_account_info = huobi_coroutine.get_account_balance(currency_code, "usdt")
                        HUOBI_CURRENCY_AMOUNT = huobi_account_info[currency_code]['balance']
                        HUOBI_USDT_AMOUNT = huobi_account_info['usdt']['balance']        

                        binance_account_info = binance_coroutine.get_account_balance(currency_code, "usdt")
                        BINANCE_CURRENCY_AMOUNT = binance_account_info[currency_code]['free']
                        BINANCE_USDT_AMOUNT = binance_account_info['usdt']['free']

                        redis.set('huobi_currency_amount', HUOBI_CURRENCY_AMOUNT)  
                        redis.set('huobi_usdt_amount', HUOBI_USDT_AMOUNT)

                        redis.set('binance_currency_amount', BINANCE_CURRENCY_AMOUNT)  
                        redis.set('binance_usdt_amount', BINANCE_USDT_AMOUNT)

                except Exception as e:
                        logger.critical("cannot initialize accout balance")
                        logger.critical(getattr(e, 'message', repr(e)))
                        logger.critical(traceback.format_exc())
                        raise
        
        redis.set('init_total_curreny_amount', float(HUOBI_CURRENCY_AMOUNT) + float(BINANCE_CURRENCY_AMOUNT))
        redis.set('init_total_usdt_amount', float(HUOBI_USDT_AMOUNT) + float(BINANCE_USDT_AMOUNT))

        table = PrettyTable()
        table.field_names = ["Platforms", currency_code.upper(), "USDT"]

        table.add_row(["HUOBI", float(redis.get('huobi_currency_amount')), float(redis.get('huobi_usdt_amount'))])
        table.add_row(["BINANCE", float(redis.get('binance_currency_amount')), float(redis.get('binance_usdt_amount'))])

        logger.info("{}{}".format("\r\n", table))
        try:
                signal.signal(signal.SIGINT, freq_analyser.write_to_csv)
        except Exception as e:
                logger.critical("cannot generate transaction statistic report")
                logger.critical(getattr(e, 'message', repr(e)))
                logger.critical(traceback.format_exc())   
                raise       
        try:
                asyncio.get_event_loop().run_until_complete(asyncio.gather(
                        huobi_coroutine.fetch_subscription(currency_code+"usdt", "step0"),
                        binance_coroutine.fetch_subscription(currency_code.upper()+"USDT"),
                        core_coroutine.bricks_checking()
                        ))
        except Exception as e: 
                logger.critical("capturing Top Level Error")
                logger.critical(getattr(e, 'message', repr(e)))
                logger.critical(traceback.format_exc())
                raise
                
        





        



