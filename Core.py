import asyncio
from datetime import datetime
from colr import Colr as C
import traceback
import json
from prettytable import PrettyTable
import configparser

config = configparser.ConfigParser()
config.read('./config.ini')

MAX_TRADE_PERCENTAGE = float(config['RULE']['max_trade_percentage'])
HUOBI_CURRENCY_AMOUNT = float(config['HUOBI']['simulated_currency_amount'])
BINANCE_CURRENCY_AMOUNT = float(config['BINANCE']['simulated_currency_amount'])
MAX_TRADE_AMOUNT = min(HUOBI_CURRENCY_AMOUNT, BINANCE_CURRENCY_AMOUNT) * MAX_TRADE_PERCENTAGE

class Core():
    def __init__(self, redis: object, currency: tuple):
        self._redis = redis
        self.currency = currency

    async def bricks_checking(self):
        # compare the records of selected platforms 
        while True:
            await asyncio.sleep(1)
            try:
                huobi_record = json.loads(self._redis.get('huobi'))
                binance_record = json.loads(self._redis.get('binance'))
            except Exception:
                print(traceback.format_exc())
            self._print_on_terminal(huobi_record, binance_record, None, render_type='normal')
            try:
                self._is_profitable(huobi_record, binance_record)
            except Exception:
                print(traceback.format_exc())

    def _is_profitable(self, a: json, b: json):

        trade_handler = {
            'huobi': self._huobi_trade_handler,
            'binance': self._binance_trade_handler
        }

        a_market = a['market']
        a_trade_rate = self._get_trade_rate(a_market)
        a_max_bid, a_bid_amount = float(a['max_bid']), float(a['bid_amount'])
        a_min_ask, a_ask_amount = float(a['min_ask']), float(a['ask_amount'])

        b_market = b['market']
        b_trade_rate = self._get_trade_rate(b_market)
        b_max_bid, b_bid_amount = float(b['max_bid']), float(b['bid_amount'])
        b_min_ask, b_ask_amount = float(b['min_ask']), float(b['ask_amount'])

        if a_max_bid > b_min_ask:
            available_trade_amount = min(a_bid_amount, b_ask_amount)
            if available_trade_amount > MAX_TRADE_AMOUNT:
                available_trade_amount = MAX_TRADE_AMOUNT

            self._print_on_terminal(a, b, available_trade_amount, render_type='trade_event')

            available_trade_amount = min(a_bid_amount, b_ask_amount)
            if available_trade_amount > MAX_TRADE_AMOUNT:
                available_trade_amount = MAX_TRADE_AMOUNT

            try:
                a_sell_result = trade_handler[a_market]('sell', a_max_bid, available_trade_amount)
            except Exception:
                print(traceback.format_exc())

            if a_sell_result:
                self._print_on_terminal('sell', a, available_trade_amount, render_type='trade_operation')
                try:
                    b_buy_result = trade_handler[b_market]('buy', b_min_ask, available_trade_amount)
                except Exception:
                    print(traceback.format_exc())
                if b_buy_result:
                    self._print_on_terminal('buy', b, available_trade_amount, render_type='trade_operation')

        if b_max_bid > a_min_ask:
            available_trade_amount = min(b_bid_amount, a_ask_amount)
            if available_trade_amount > MAX_TRADE_AMOUNT:
                available_trade_amount = MAX_TRADE_AMOUNT

            self._print_on_terminal(b, a, available_trade_amount, render_type='trade_event')

            try:
                b_sell_result = trade_handler[b_market]('sell', b_max_bid, available_trade_amount)
            except Exception:
                print(traceback.format_exc())
                
            if b_sell_result:
                self._print_on_terminal('sell', b, available_trade_amount, render_type='trade_operation')
                try:
                    a_buy_result = trade_handler[a_market]('buy', a_min_ask, available_trade_amount)
                except Exception:
                    print(traceback.format_exc())
                if a_buy_result:
                    self._print_on_terminal('buy', b, available_trade_amount, render_type='trade_operation')

        self._print_on_terminal(None, None, None, render_type='status')

    def _get_trade_rate(self, market):
        pass

    def _huobi_trade_handler(self, operation: str, price: float, amount: float):
        if self._redis.get('exec_mode') == b'simulation':
            
            if operation == 'sell':
                new_currency_amount = float(self._redis.get('huobi_currency_amount')) - amount
                self._redis.set('huobi_currency_amount', new_currency_amount)
                new_usdt_amount = float(self._redis.get('huobi_usdt_amount')) + amount * price
                self._redis.set('huobi_usdt_amount', new_usdt_amount)
                return True

            if operation == 'buy':
                new_currency_amount = float(self._redis.get('huobi_currency_amount')) + amount
                self._redis.set('huobi_currency_amount', new_currency_amount)
                new_usdt_amount = float(self._redis.get('huobi_usdt_amount')) - amount * price
                self._redis.set('huobi_usdt_amount', new_usdt_amount)
                return True
        else:
            exit('to do production')

    def _binance_trade_handler(self, operation: str, price: float, amount: float):
        if self._redis.get('exec_mode') == b'simulation':

            if operation == 'sell':
                new_currency_amount = float(self._redis.get('binance_currency_amount')) - amount
                self._redis.set('binance_currency_amount', new_currency_amount)
                new_usdt_amount = float(self._redis.get('binance_usdt_amount')) + amount * price
                self._redis.set('binance_usdt_amount', new_usdt_amount)
                return True

            if operation == 'buy':
                new_currency_amount = float(self._redis.get('binance_currency_amount')) + amount
                self._redis.set('binance_currency_amount', new_currency_amount)
                new_usdt_amount = float(self._redis.get('binance_usdt_amount')) - amount * price
                self._redis.set('binance_usdt_amount', new_usdt_amount)
                return True
        else:
            exit('to do production')        

    def _print_on_terminal(self, *data, render_type='normal'):
        try:
            a_record = data[0] # in render_type='trade_operation' a_record changes its semantic to a trade signal 'sold' | 'purchsed'
            b_record = data[1] # in render_type='trade_operation' a_record changes its semantic to a trade information cluster
            operable_amount = data[2]
        except Exception:
            print(traceback.format_exc())
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print('----------------------------------'+self.currency[1]+'------------------------------\r\n'+time)
        
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
            msg = '\r\n>>>>>>>>>>>>>>>>>>>>>>Trade Event<<<<<<<<<<<<<<<<<<<<\r\n--->{} max bid: {} > {} min ask: {} --- available amount: {} --- operable amount: {}\r\n'.\
                        format(a_record['market'], a_record['max_bid'], b_record['market'], b_record['min_ask'], available_amount, operable_amount)
            
            print(C().normal().red(msg))

        if render_type == 'status':
            table = PrettyTable()
            table.field_names = ["Platforms", self.currency[1], "USDT"]
            if self._redis.get('exec_mode') == b'simulation':
                table.add_row(["HUOBI", float(self._redis.get('huobi_currency_amount')), float(self._redis.get('huobi_usdt_amount'))])
                table.add_row(["BINANCE", float(self._redis.get('binance_currency_amount')), float(self._redis.get('binance_usdt_amount'))])
                print(table)
            else:
                print('print for prod status')

        if render_type == 'trade_operation':
            if a_record == 'sell':
                operation_price = float(b_record['max_bid']) * float(b_record['bid_amount'])
                msg = '---> {} {} were sold in {} with the price {} usdt'.format(operable_amount, self.currency[0].upper(), b_record['market'], str(operation_price))
            elif a_record == 'buy':
                operation_price = float(b_record['min_ask']) * float(b_record['ask_amount'])
                msg = '---> {} {} were purchased in {} with the price {} usdt'.format(operable_amount, self.currency[0].upper(), b_record['market'], str(operation_price))
            print(C().normal().red(msg))