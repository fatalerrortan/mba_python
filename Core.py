import asyncio
from datetime import datetime
from colr import Colr as C
import traceback
import json
from prettytable import PrettyTable
import configparser
import logging

config = configparser.ConfigParser()
config.read('./config.ini')

MAX_TRADE_PERCENTAGE = float(config['RULE']['max_trade_percentage'])

HUOBI_CURRENCY_AMOUNT = float(config['HUOBI']['simulated_currency_amount'])
BINANCE_CURRENCY_AMOUNT = float(config['BINANCE']['simulated_currency_amount'])
INIT_TOTAL_CURRENCY_AMOUNT = HUOBI_CURRENCY_AMOUNT + BINANCE_CURRENCY_AMOUNT
MAX_TRADE_AMOUNT = min(HUOBI_CURRENCY_AMOUNT, BINANCE_CURRENCY_AMOUNT) * MAX_TRADE_PERCENTAGE

HUOBI_USDT_AMOUNT = float(config['HUOBI']['simulated_usdt_amount'])
BINANCE_USDT_AMOUNT = float(config['BINANCE']['simulated_usdt_amount'])
INIT_TOTAL_USDT_AMOUNT = HUOBI_USDT_AMOUNT + BINANCE_USDT_AMOUNT

logger = logging.getLogger('core_logger')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('logs/core.log')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

class Core():
    def __init__(self, redis: object, currency: str, freq_analyser: object):
        self._redis = redis
        self.currency = (currency, '{} / usdt'.format(currency).upper())# param0: currency code; param1: curreny / usdt
        self.freq_analyser = freq_analyser

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
                next_step = self._is_profitable(huobi_record, binance_record)
                if next_step == 'continue': continue
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

            margin = round(a_max_bid - b_min_ask, 3)
            if not margin == 0:
                if not margin in self.freq_analyser.freq_margin_list:
                    self.freq_analyser.set_freq(margin, new_item=True)
                else:
                    self.freq_analyser.set_freq(margin)
                
            a_pre_result = trade_handler[a_market]('sell', a_max_bid, available_trade_amount, advance_mode=True)
            b_pre_result = trade_handler[b_market]('buy', b_min_ask, available_trade_amount, advance_mode=True)

            if not a_pre_result == None and not b_pre_result == None:
                try:
                    a_sell_result = trade_handler[a_market]('sell', a_max_bid, available_trade_amount)
                    if a_sell_result:
                        self._print_on_terminal('sell', a, available_trade_amount, render_type='trade_operation')
                        try:
                            b_buy_result = trade_handler[b_market]('buy', b_min_ask, available_trade_amount)
                        except Exception:
                            print(traceback.format_exc())
                        if b_buy_result:
                            self._print_on_terminal('buy', b, available_trade_amount, render_type='trade_operation')
                        else:
                            self._print_on_terminal(b_market, None, None, render_type='continue')
                            return 'continue'       
                    else:
                        self._print_on_terminal(a_market, None, None, render_type='continue')
                        return 'continue'       
                except Exception:
                    print(traceback.format_exc())
            else: 
                self._print_on_terminal(None, None, None, render_type='continue')
                return 'continue'


        if b_max_bid > a_min_ask:

            available_trade_amount = min(b_bid_amount, a_ask_amount)
            if available_trade_amount > MAX_TRADE_AMOUNT:
                available_trade_amount = MAX_TRADE_AMOUNT

            self._print_on_terminal(b, a, available_trade_amount, render_type='trade_event')

            margin = round(b_max_bid - a_min_ask, 3)
            if not margin == 0:
                if not margin in self.freq_analyser.freq_margin_list:
                    self.freq_analyser.set_freq(margin, new_item=True)
                else:
                    self.freq_analyser.set_freq(margin)

            b_pre_result = trade_handler[b_market]('sell', b_max_bid, available_trade_amount, advance_mode=True)
            a_pre_result = trade_handler[a_market]('buy', a_min_ask, available_trade_amount, advance_mode=True)

            if not b_pre_result == None and not a_pre_result == None:
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
                    else: 
                        self._print_on_terminal(a_market, None, None, render_type='continue')
                        return 'continue'            
                else:
                    self._print_on_terminal(b_market, None, None, render_type='continue')
                    return 'continue'            
            else:
                self._print_on_terminal(None, None, None, render_type='continue')
                return 'continue'

        self._print_on_terminal(None, None, None, render_type='status')

    def _get_trade_rate(self, market):
        pass

    def _huobi_trade_handler(self, operation: str, price: float, amount: float, advance_mode=None):
        if self._redis.get('exec_mode') == b'simulation':
            
            if operation == 'sell':
                new_currency_amount = float(self._redis.get('huobi_currency_amount')) - amount
                new_usdt_amount = float(self._redis.get('huobi_usdt_amount')) + amount * price
                if advance_mode:
                    if new_currency_amount <= 0 or new_usdt_amount <= 0:
                        return None
                    else: return True
                else:
                    self._redis.set('huobi_currency_amount', new_currency_amount)
                    self._redis.set('huobi_usdt_amount', new_usdt_amount)
                    return True

            if operation == 'buy':
                new_currency_amount = float(self._redis.get('huobi_currency_amount')) + amount
                new_usdt_amount = float(self._redis.get('huobi_usdt_amount')) - amount * price
                if advance_mode:
                    if new_currency_amount <= 0 or new_usdt_amount <= 0:
                        return None
                    else: return True
                else:
                    self._redis.set('huobi_currency_amount', new_currency_amount)
                    self._redis.set('huobi_usdt_amount', new_usdt_amount)
                    return True
        else:
            exit('to do production')

    def _binance_trade_handler(self, operation: str, price: float, amount: float, advance_mode=None):
        if self._redis.get('exec_mode') == b'simulation':

            if operation == 'sell':
                new_currency_amount = float(self._redis.get('binance_currency_amount')) - amount
                new_usdt_amount = float(self._redis.get('binance_usdt_amount')) + amount * price
                if advance_mode:
                    if new_currency_amount <= 0 or new_usdt_amount <= 0:
                        return None
                    else: return True
                else:
                    self._redis.set('binance_currency_amount', new_currency_amount)
                    self._redis.set('binance_usdt_amount', new_usdt_amount)
                    return True

            if operation == 'buy':
                new_currency_amount = float(self._redis.get('binance_currency_amount')) + amount
                new_usdt_amount = float(self._redis.get('binance_usdt_amount')) - amount * price
                if advance_mode:
                    if new_currency_amount <= 0 or new_usdt_amount <= 0:
                        return None
                    else: return True
                else:
                    self._redis.set('binance_currency_amount', new_currency_amount)
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
        title = '----------------------------------'+self.currency[1]+'------------------------------\r\n'+time
        print(title)
        # logger.info(title)

        if render_type == 'normal':
            a_msg = '{} -> (max bid: {:.20f}, amount: {:.20f}); (min ask: {:.20f}, amount: {:.20f})'\
                    .format(str(a_record['market']), a_record['max_bid'], a_record['bid_amount'],\
                    a_record['min_ask'], a_record['ask_amount'])
            b_msg = '{} -> (max bid: {:.20f}, amount: {:.20f}), (min ask: {:.20f}, amount: {:.20f})'\
                    .format(str(b_record['market']), b_record['max_bid'], b_record['bid_amount'],\
                    b_record['min_ask'], b_record['ask_amount'])
            
            print(C().normal().green(a_msg))
            print(C().normal().bright().blue(b_msg))
            # logger.info(a_msg)
            # logger.info(b_msg)

        if render_type == 'trade_event':
            available_amount = min(float(a_record['bid_amount']), float(b_record['ask_amount']))
            msg = '\r\n>>>>>>>>>>>>>>>>>>>>>>Trade Event<<<<<<<<<<<<<<<<<<<<\r\n--->{} max bid: {:.20f} > {} min ask: {:.20f} --- available amount: {:.20f} --- operable amount: {:.20f}\r\n'.\
                        format(a_record['market'], float(a_record['max_bid']), b_record['market'], float(b_record['min_ask']), available_amount, operable_amount)
            
            print(C().normal().red(msg))
            # logger.info(msg)

        if render_type == 'status':
            table = PrettyTable()
            table.field_names = ["Platforms", self.currency[0].upper(), "USDT"]
            if self._redis.get('exec_mode') == b'simulation':
                table.add_row(["HUOBI", round( float(self._redis.get('huobi_currency_amount')), 20), round( float(self._redis.get('huobi_usdt_amount')) , 20)])
                table.add_row(["BINANCE", round(float(self._redis.get('binance_currency_amount')), 20), round(float(self._redis.get('binance_usdt_amount')), 20)])
                print(table)
                # logger.info(table)
                
                currency_profit = float(self._redis.get('huobi_currency_amount')) + float(self._redis.get('binance_currency_amount')) - INIT_TOTAL_CURRENCY_AMOUNT
                usdt_profit = float(self._redis.get('huobi_usdt_amount')) + float(self._redis.get('binance_usdt_amount')) - INIT_TOTAL_USDT_AMOUNT
                msg = '---> initial {} amount / profit: {} / {:.20f} <--- \r\n---> initial usdt amount / profit: {} / {:.20f} <---'.\
                    format(self.currency[0], INIT_TOTAL_CURRENCY_AMOUNT, currency_profit, INIT_TOTAL_USDT_AMOUNT, usdt_profit)
                print(C(msg, fore=190))
                # logger.info(msg)
            else:
                print('print for prod status')

        if render_type == 'trade_operation':
            if a_record == 'sell':
                operation_total_price = float(b_record['max_bid']) * float(operable_amount)
                msg = '---> {:.20f} {} were sold in {} with the price {:.20f} usdt <---'.format(operable_amount, self.currency[0].upper(), b_record['market'], operation_total_price)
            elif a_record == 'buy':
                operation_total_price = float(b_record['min_ask']) * float(operable_amount)
                msg = '---> {:.20f} {} were purchased in {} with the price {:.20f} usdt <---'.format(operable_amount, self.currency[0].upper(), b_record['market'], operation_total_price)
            print(C().normal().red(msg))
            # logger.info(msg)

        if render_type == 'continue':
            if a_record:
                msg = '---> {} platform cannot confirm this trade, then breaking this transaction and waiting for the next <---'.format(a_record)
            else:
                msg = '--->  this trade cannot be handled in terms of account balance, waiting for the next <---'

            print(C().normal().red(msg))
            # logger.info(msg)
            self._print_on_terminal(None, None, None, render_type='status')