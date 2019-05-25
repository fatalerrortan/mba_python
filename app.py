from platforms.Huobi import Huobi
from platforms.Binance import Binance
from Core import Core
import asyncio
import redis
import configparser

config = configparser.ConfigParser()
config.read('./config.ini')

EXEC_MODE = config['MODE']['mode']
CURRENCY = {
        config['MODE']['currency_code']: 'ETH / USDT' 
}

HUOBI_WS_URL = config['HUOBI']['ws_url']
HUOBI_TOPIC_MARKET_DEPTH = config['HUOBI']['stream']
huobi_currency_amount = config['HUOBI']['simulated_currency_amount']
huobi_ustd_amount = config['HUOBI']['simulated_usdt_amount']

BINANCE_WS_URL = config['BINANCE']['ws_url']
BINANCE_STREAM = config['BINANCE']['stream']
binance_currency_amount = config['BINANCE']['simulated_currency_amount']
binance_ustd_amount = config['BINANCE']['simulated_usdt_amount']

REDIS_URL = config['DATABASE']['redis_url']
REDIS_PORT = config['DATABASE']['redis_port']

if __name__ == '__main__':
        redis = redis.Redis(host=REDIS_URL, port=REDIS_PORT, db=0)

        if EXEC_MODE == 'simulation':
                redis.set('huobi_currency_amount', config['HUOBI']['simulated_currency_amount'])  
                redis.set('huobi_ustd_amount', config['HUOBI']['simulated_usdt_amount'])
                redis.set('binance_currency_amount', config['BINANCE']['simulated_currency_amount'])  
                redis.set('binance_ustd_amount', config['BINANCE']['simulated_usdt_amount'])          

        binance_coroutine = Binance(BINANCE_WS_URL+BINANCE_STREAM, redis)
        huobi_coroutine = Huobi(HUOBI_WS_URL, redis)    
        core_coroutine = Core(redis, CURRENCY['ethusdt'])

        asyncio.get_event_loop().run_until_complete(asyncio.gather(
                huobi_coroutine.fetch_subscription(sub=HUOBI_TOPIC_MARKET_DEPTH), 
                binance_coroutine.fetch_subscription(),
                core_coroutine.bricks_checking()
                ))
   