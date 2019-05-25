import asyncio
from datetime import datetime
from colr import Colr as C
import traceback
import json

class Core():
    def __init__(self, redis: object, currency: str):
        self.redis = redis
        self.currency = currency

    async def bricks_checking(self):
        # compare the records of selected platforms 
        while True:
            await asyncio.sleep(1)
            try:
                huobi_record = json.loads(self.redis.get('huobi'))
                binance_record = json.loads(self.redis.get('binance'))
            except Exception:
                print(traceback.format_exc())
            self._print_on_terminal(huobi_record, binance_record, render_type='normal')
            try:
                self._is_profitable(huobi_record, binance_record)
            except Exception:
                print(traceback.format_exc())

    def _is_profitable(self, a: json, b: json):
        a_market = a['market']
        a_trade_rate = self._get_trade_rate(a_market)
        a_max_bid, a_bid_amount = a['max_bid'], a['bid_amount']
        a_min_ask, a_ask_amount = a['min_ask'], a['ask_amount']

        b_market = b['market']
        b_trade_rate = self._get_trade_rate(b_market)
        b_max_bid, b_bid_amount = b['max_bid'], b['bid_amount']
        b_min_ask, b_ask_amount = b['min_ask'], b['ask_amount']

        if a_max_bid > b_min_ask:
            self._print_on_terminal(a, b, render_type='trade_event')

        if b_max_bid > a_min_ask:
            self._print_on_terminal(b, a, render_type='trade_event')

    def _get_trade_rate(self, market):
        pass

    def _do_trade(self):
        pass

    def _print_on_terminal(self, *data, render_type='normal'):
        try:
            a_record = data[0]
            b_record = data[1]
        except Exception:
            print(traceback.format_exc())
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print('----------------------------------'+self.currency+'------------------------------\r\n'+time)
        
        if render_type == 'normal':
            a_msg = '{} -> (max bid: {}, amount: {}); (min ask: {}, amount: {})'\
                    .format(str(a_record['market']), str(a_record['max_bid']), str(a_record['bid_amount']),\
                    str(a_record['min_ask']), str(a_record['ask_amount']))
            b_msg = '{} -> (max bid: {}, amount: {}), (min ask: {}, amount: {})'\
                    .format(str(b_record['market']), str(b_record['max_bid']), str(b_record['bid_amount']),\
                    str(b_record['min_ask']), str(b_record['ask_amount']))
            
            print(C().normal().green(a_msg))
            print(C().normal().bright().blue(b_msg))

        if render_type == 'trade_event':
            available_amount = str(min(float(a_record['bid_amount']), float(b_record['ask_amount'])))
            msg = '\r\n>>>>>>>>>>>>>>>>>>>>>>Trade Event<<<<<<<<<<<<<<<<<<<<\r\n--->{} max bid: {} > {} min ask: {} --- available amount: {}\r\n'.\
                        format(a_record['market'], a_record['max_bid'], b_record['market'], b_record['min_ask'], available_amount)
            
            print(C().normal().red(msg))