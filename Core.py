import asyncio
from datetime import datetime
from colr import Colr as C
import traceback
import json

class Core():

    def __init__(self, redis: object):
        self.redis = redis

    async def bricks_checking(self):
        # compare the records of selected platforms 
        while True:
            await asyncio.sleep(1)
            try:
                huobi_record = json.loads(self.redis.get('huobi'))
                binance_record = json.loads(self.redis.get('binance'))
            except Exception:
                print(traceback.format_exc())
            # self._print_on_terminal(huobi_record, binance_record, render_type='normal')
            try:
                self._is_profitable(huobi_record, binance_record)
            except Exception:
                print(traceback.format_exc())

    def _is_profitable(self, a: json, b: json):
        a_trade_rate = self._get_trade_rate(a['market'])
        a_max_bid, a_bid_amount = a['max_bid'], a['bid_amount']
        a_min_ask, a_ask_amount = a['min_ask'], a['ask_amount']
        
        b_trade_rate = self._get_trade_rate(b['market'])
        b_max_bid, b_bid_amount = b['max_bid'], b['bid_amount']
        b_min_ask, b_ask_amount = b['min_ask'], b['ask_amount']

        async def _compare(max_bid, min_ask):
            if max_bid > min_ask:
                print('!!!!!!!!!!!!!!!!TRADE EVENT!!!!!!!!!!!!! bid {} > ask {}'.format(max_bid, min_ask))               
            
        asyncio.get_event_loop().run_until_complete(asyncio.gather(
                _compare(a_max_bid, b_min_ask),
                _compare(b_max_bid, a_min_ask)
            ))
        
    def _get_trade_rate(self, market):
        pass

    def _do_trade(self):
        pass

    def _print_on_terminal(*data, render_type='normal'):
        try:
            huobi_record = data[1]
            binance_record = data[2]
        except Exception:
            print(traceback.format_exc())
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        huobi_msg = 'Huobi -> (max bid: {}, amount: {}); (min ask: {}, amount: {})'\
                .format(str(huobi_record['max_bid']), str(huobi_record['bid_amount']),\
                str(huobi_record['min_ask']), str(huobi_record['ask_amount']))
        binance_msg = 'Binance -> (max bid: {}, amount: {}), (min ask: {}, amount: {})'\
                .format(str(binance_record['max_bid']), str(binance_record['bid_amount']),\
                str(binance_record['min_ask']), str(binance_record['ask_amount']))
        print('---------------------------------------------------------------------\r\n'+time)
        print(C().normal().green(huobi_msg))
        print(C().normal().bright().blue(binance_msg))
        