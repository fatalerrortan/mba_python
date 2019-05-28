from platforms.Huobi import Huobi
from platforms.Binance import Binance
from Core import Core
import asyncio
import redis
import configparser
from prettytable import PrettyTable

config = configparser.ConfigParser()
config.read('./config.ini')

EXEC_MODE = config['MODE']['mode']
CURRENCY = {
        config['MODE']['currency_code']: 'ETH / USDT' 
}



HUOBI_WS_URL = config['HUOBI']['ws_url']
HUOBI_TOPIC_MARKET_DEPTH = config['HUOBI']['stream']
HUOBI_CURRENCY_AMOUNT = config['HUOBI']['simulated_currency_amount']
HUOBI_USDT_AMOUNT = config['HUOBI']['simulated_usdt_amount']

BINANCE_WS_URL = config['BINANCE']['ws_url']
BINANCE_STREAM = config['BINANCE']['stream']
BINANCE_CURRENCY_AMOUNT = config['BINANCE']['simulated_currency_amount']
BINANCE_USDT_AMOUNT = config['BINANCE']['simulated_usdt_amount']

REDIS_URL = config['DATABASE']['redis_url']
REDIS_PORT = config['DATABASE']['redis_port']

if __name__ == '__main__':
        redis = redis.Redis(host=REDIS_URL, port=REDIS_PORT, db=0)
        if EXEC_MODE == 'simulation':
                redis.set('exec_mode', 'simulation')
                redis.set('huobi_currency_amount', HUOBI_CURRENCY_AMOUNT)  
                redis.set('huobi_usdt_amount', HUOBI_USDT_AMOUNT)
                redis.set('binance_currency_amount', BINANCE_CURRENCY_AMOUNT)  
                redis.set('binance_usdt_amount', BINANCE_USDT_AMOUNT)          

        binance_coroutine = Binance(BINANCE_WS_URL+BINANCE_STREAM, redis)
        huobi_coroutine = Huobi(HUOBI_WS_URL, redis)    
        core_coroutine = Core(redis, (config['MODE']['currency_code'], CURRENCY['eth']))

        table = PrettyTable()
        table.field_names = ["Platforms", config['MODE']['currency_code'].upper(), "USDT"]
        table.add_row(["HUOBI", float(redis.get('huobi_currency_amount')), float(redis.get('huobi_usdt_amount'))])
        table.add_row(["BINANCE", float(redis.get('binance_currency_amount')), float(redis.get('binance_usdt_amount'))])
        print(table)

        asyncio.get_event_loop().run_until_complete(asyncio.gather(
                huobi_coroutine.fetch_subscription(sub=HUOBI_TOPIC_MARKET_DEPTH), 
                binance_coroutine.fetch_subscription(),
                core_coroutine.bricks_checking()
                ))
   