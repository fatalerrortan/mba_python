from platforms.Huobi import Huobi
import asyncio

HUOBI_WS_URL = 'wss://api.huobi.pro/ws'
HUOBI_TOPIC_TRADE_DETAIL = '{ \
        "sub": "market.ethusdt.trade.detail","id": "" \
        }'
HUOBI_TOPIC_MARKET_DEPTH = '{ \
        "sub": "market.ethusdt.depth.step0","id": "" \
        }'

if __name__ == '__main__':

    Huobi_platform = Huobi(ws_url=HUOBI_WS_URL)    
    huobi_trade_record = Huobi_platform.fetch_subscription(sub=HUOBI_TOPIC_MARKET_DEPTH)
    # for item in huobi_trade_record:
    #     print(item)
#     while True:
#         print(next(huobi_trade_record))