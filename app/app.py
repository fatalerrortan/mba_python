from platforms.Huobi import Huobi
from platforms.Binance import Binance
from Core import Core
import asyncio
import redis
from pymemcache.client.base import Client as Memcached_Cient
import configparser
from prettytable import PrettyTable
from analyser.Freq_Analyser import Freq_Analyser
import signal
import logging
import datetime
import sys
import os
import subprocess

currency_code = input("---> pls input your crypto currency code: ")
 
logger = logging.getLogger("root")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s / %(levelname)s / %(name)s / %(message)s")

sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
sh.setFormatter(formatter)

dt = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

if not os.path.isdir("logs"):
        os.makedirs("logs", os.umask(0))

fh = logging.FileHandler("logs/{}_{}.log".format(dt, currency_code))
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)

logger.addHandler(sh)
logger.addHandler(fh)

config = configparser.ConfigParser()
config.read('etc/{}.ini'.format(currency_code))

EXEC_MODE = input("---> if simulation mode, pls type 'yes' otherwise pls type 'no' to run production mode: ")
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

Memcached_URL = config['DATABASE']['memcached_url']
Memcached_PORT = int(config['DATABASE']['memcached_port'])

if __name__ == '__main__':
        
        logger.info(">>> TanMba is running <<<")

        try:
                subprocess.Popen("memcached.exe start")
                memcached = Memcached_Cient((Memcached_URL, Memcached_PORT))
                memcached.set('currency_code', currency_code)
                memcached.set('trade_rule_file', TRADE_RULE_FILE)
        except Exception:
                logger.critical(Exception)
                raise Exception
        
        binance_coroutine = Binance(BINANCE_WS_URL+BINANCE_STREAM, BINANCE_API_HOST, memcached, BINANCE_API_KEY, BINANCE_SECRET_KEY)
        huobi_coroutine = Huobi(HUOBI_WS_URL, HUOBI_API_HOST, memcached, HUOBI_API_KEY, HUOBI_SECRET_KEY)    
        freq_analyser = Freq_Analyser(currency_code)
        core_coroutine = Core(memcached, currency_code, freq_analyser) 

        # yes => simulation mode
        if EXEC_MODE == 'yes':

                memcached.set('exec_mode', 'simulation')

                memcached.set('huobi_currency_amount', HUOBI_CURRENCY_AMOUNT)  
                memcached.set('huobi_usdt_amount', HUOBI_USDT_AMOUNT)

                memcached.set('binance_currency_amount', BINANCE_CURRENCY_AMOUNT)  
                memcached.set('binance_usdt_amount', BINANCE_USDT_AMOUNT)

        else:
                memcached.set('exec_mode', 'production')
                
                try:
                        huobi_account_info = huobi_coroutine.get_account_balance(currency_code, "usdt")
                        HUOBI_CURRENCY_AMOUNT = huobi_account_info[currency_code]['balance']
                        HUOBI_USDT_AMOUNT = huobi_account_info['usdt']['balance']        

                        binance_account_info = binance_coroutine.get_account_balance(currency_code, "usdt")
                        BINANCE_CURRENCY_AMOUNT = binance_account_info[currency_code]['free']
                        BINANCE_USDT_AMOUNT = binance_account_info['usdt']['free']

                        memcached.set('huobi_currency_amount', HUOBI_CURRENCY_AMOUNT)  
                        memcached.set('huobi_usdt_amount', HUOBI_USDT_AMOUNT)

                        memcached.set('binance_currency_amount', BINANCE_CURRENCY_AMOUNT)  
                        memcached.set('binance_usdt_amount', BINANCE_USDT_AMOUNT)

                except Exception:
                        logger.critical("cannot initialize accout balance")
                        logger.critical(Exception)
                        raise
        
        memcached.set('init_total_curreny_amount', float(HUOBI_CURRENCY_AMOUNT) + float(BINANCE_CURRENCY_AMOUNT))
        memcached.set('init_total_usdt_amount', float(HUOBI_USDT_AMOUNT) + float(BINANCE_USDT_AMOUNT))

        table = PrettyTable()
        table.field_names = ["Platforms", currency_code.upper(), "USDT"]

        table.add_row(["HUOBI", float(memcached.get('huobi_currency_amount')), float(memcached.get('huobi_usdt_amount'))])
        table.add_row(["BINANCE", float(memcached.get('binance_currency_amount')), float(memcached.get('binance_usdt_amount'))])

        logger.info("{}{}".format("\r\n", table))
        try:
                signal.signal(signal.SIGINT, freq_analyser.write_to_csv)
        except Exception:
                logger.critical("cannot generate transaction statistic report")
                logger.critical(Exception)   
                raise       
        try:

                asyncio.get_event_loop().run_until_complete(asyncio.gather(
                        huobi_coroutine.fetch_subscription(sub=HUOBI_TOPIC_MARKET_DEPTH),
                        binance_coroutine.fetch_subscription(),
                        core_coroutine.bricks_checking()
                        ))

        except Exception: 
                logger.critical("capturing Top Level Error")
                logger.critical(Exception)
                raise
                
        
        
        
   
        