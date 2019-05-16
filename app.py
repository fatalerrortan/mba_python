from platforms.Huobi import Huobi
from Core import Core
import asyncio
import redis

HUOBI_WS_URL = 'wss://api.huobi.pro/ws'
HUOBI_TOPIC_TRADE_DETAIL = '{ \
        "sub": "market.ethusdt.trade.detail","id": "" \
        }'
HUOBI_TOPIC_MARKET_DEPTH = '{ \
        "sub": "market.ethusdt.depth.step0","id": "" \
        }'

if __name__ == '__main__':
        Redis = redis.Redis(host='localhost', port=6379, db=0)
        Huobi_platform = Huobi(HUOBI_WS_URL, Redis)    
        Core = Core(Redis)
        asyncio.get_event_loop().run_until_complete(asyncio.gather(
                Huobi_platform.fetch_subscription(sub=HUOBI_TOPIC_MARKET_DEPTH), 
                Core.bricks_checking()
                ))
   