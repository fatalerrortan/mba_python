from platforms.Huobi import Huobi
from platforms.Binance import Binance
from Core import Core
import asyncio
import redis

HUOBI_WS_URL = 'wss://api.huobi.pro/ws'
BINANCE_WS_URL = 'wss://stream.binance.com:9443/ws/'
BINANCE_STREAM = 'ethusdt@depth20'

HUOBI_TOPIC_TRADE_DETAIL = '{ \
        "sub": "market.ethusdt.trade.detail","id": "" \
        }'
HUOBI_TOPIC_MARKET_DEPTH = '{ \
        "sub": "market.ethusdt.depth.step0","id": "" \
        }'

if __name__ == '__main__':
        redis = redis.Redis(host='localhost', port=6379, db=0)

        binance_coroutine = Binance(BINANCE_WS_URL+BINANCE_STREAM, redis)
        huobi_coroutine = Huobi(HUOBI_WS_URL, redis)    
        core_coroutine = Core(redis)

        asyncio.get_event_loop().run_until_complete(asyncio.gather(
                huobi_coroutine.fetch_subscription(sub=HUOBI_TOPIC_MARKET_DEPTH), 
                binance_coroutine.fetch_subscription(),
                core_coroutine.bricks_checking()
                ))
        # asyncio.get_event_loop().run_until_complete(binance_coroutine.fetch_subscription())
   