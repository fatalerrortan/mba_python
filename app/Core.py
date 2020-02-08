import asyncio
from datetime import datetime
import traceback
import json
from prettytable import PrettyTable
import configparser
import logging
from platforms.Huobi import Huobi
from platforms.Binance import Binance

config = configparser.ConfigParser()
config.read('etc/config_dev.ini')

HUOBI_CURRENCY_AMOUNT = float(config['HUOBI']['simulated_currency_amount'])
BINANCE_CURRENCY_AMOUNT = float(config['BINANCE']['simulated_currency_amount'])
INIT_TOTAL_CURRENCY_AMOUNT = HUOBI_CURRENCY_AMOUNT + BINANCE_CURRENCY_AMOUNT

HUOBI_USDT_AMOUNT = float(config['HUOBI']['simulated_usdt_amount'])
BINANCE_USDT_AMOUNT = float(config['BINANCE']['simulated_usdt_amount'])
INIT_TOTAL_USDT_AMOUNT = HUOBI_USDT_AMOUNT + BINANCE_USDT_AMOUNT

TRADE_RULE_FILE = config['RULE']['rule_file']

class Core():
    def __init__(self, redis: object, currency: str, freq_analyser: object):

        self.logger = logging.getLogger("root.{}".format(__name__))
        self._redis = redis
        self.currency = (currency, '{} / usdt'.format(currency).upper())# param0: currency code; param1: curreny / usdt
        self.freq_analyser = freq_analyser
        self.trade_rule_json = self._get_trade_rules(currency)

    async def bricks_checking(self):
        # compare the records of selected platforms 
        while True:
            await asyncio.sleep(1)

            try:
                huobi_record = json.loads(self._redis.get('huobi'))
                binance_record = json.loads(self._redis.get('binance'))
                self._print_on_terminal(huobi_record, binance_record, None, render_type='normal')
            except Exception:
                self.logger.warning("cannot retrieve current bid and sell records from redis")
                self.logger.warning(Exception)
                continue
            
            self._is_profitable(huobi_record, binance_record)
            self._is_profitable(binance_record, huobi_record)

    
    def _is_profitable(self, a: json, b: json):

        trade_handler = {
            'huobi': self._huobi_trade_handler,
            'binance': self._binance_trade_handler
        }

        a_market = a['market']
        #a_trade_rate = self._get_trade_rate(a_market)
        a_max_bid, a_bid_amount = float(a['max_bid']), float(a['bid_amount'])
        a_min_ask, a_ask_amount = float(a['min_ask']), float(a['ask_amount'])

        b_market = b['market']
        #b_trade_rate = self._get_trade_rate(b_market)
        b_max_bid, b_bid_amount = float(b['max_bid']), float(b['bid_amount'])
        b_min_ask, b_ask_amount = float(b['min_ask']), float(b['ask_amount'])

        if a_max_bid > b_min_ask:

            available_trade_amount = min(a_bid_amount, b_ask_amount)
            margin = a_max_bid - b_min_ask
            
            if not round(margin, 4) == 0:
                self.freq_analyser.set_freq(round(margin, 4)) 
                try:
                    rule_label, trade_rate, MAX_TRADE_AMOUNT = self._get_max_trade_amount(margin)
                except Exception:
                    self.logger.critical("cannot get max trade amount, it could be caused by reading undefined trade rule rules/testing.json")
                    self.logger.critical(Exception)
                    raise

                if MAX_TRADE_AMOUNT:
                    if available_trade_amount > MAX_TRADE_AMOUNT:
                        available_trade_amount = MAX_TRADE_AMOUNT
                    
                    self._print_on_terminal(a, b, available_trade_amount, render_type='trade_event')
                    self._print_on_terminal(margin, rule_label, trade_rate, render_type='trade_rule')

                    try:
                        a_pre_result = trade_handler[a_market]('sell', a_max_bid, available_trade_amount, advance_mode=True)
                        b_pre_result = trade_handler[b_market]('buy', b_min_ask, available_trade_amount, advance_mode=True)
                    except Exception:
                        self.logger.critical("transaction pre check mode failed")
                        self.logger.critical(Exception)
                        raise   

                    if a_pre_result and b_pre_result:
                        a_sell_result = trade_handler[a_market]('sell', a_max_bid, available_trade_amount)
                        if a_sell_result:
                            self._print_on_terminal('sell', a, available_trade_amount, render_type='trade_operation')
                            b_buy_result = trade_handler[b_market]('buy', b_min_ask, available_trade_amount)
                            if b_buy_result:
                                self._print_on_terminal('buy', b, available_trade_amount, render_type='trade_operation')
                            else:
                                self._print_on_terminal(b_market, None, None, render_type='continue')
                            try:
                                if not self._redis.get('exec_mode') == b'simulation':
                                    self.account_update()
                            except Exception:
                                self.logger.critical("cannot update accout balance after transaction")
                                self.logger.critical(Exception)
                                raise
                            self._print_on_terminal(None, None, None, render_type='status') 
                        else:
                            self._print_on_terminal(a_market, None, None, render_type='continue')                                 
                    else:
                        self._print_on_terminal(None, None, None, render_type='continue')                      

    def _get_trade_rate(self, market):
        return 0
    
    def _get_trade_rules(self, currency):
        with open('rules/{}'.format(TRADE_RULE_FILE)) as trade_rule_file:
            try:
                trade_rule_json = json.load(trade_rule_file)[currency] 
            except KeyError:
                self.logger.warning('cannot find pre-defined trade rule, using default')    
                return self._get_trade_rules('default')
            return trade_rule_json    

    def _huobi_trade_handler(self, operation: str, price: float, amount: float, advance_mode=None):
            
        order_size = price * amount

        if order_size <= 10: return None

        if operation == 'sell':
            new_currency_amount = float(self._redis.get('huobi_currency_amount')) - amount
            new_usdt_amount = float(self._redis.get('huobi_usdt_amount')) + amount * price
            if advance_mode:
                if new_currency_amount >= 0 and new_usdt_amount >= 0:
                    return True
                else: return None
            else:
                if self._redis.get('exec_mode') == b'simulation':
                    self._redis.set('huobi_currency_amount', new_currency_amount)
                    self._redis.set('huobi_usdt_amount', new_usdt_amount)
                    return True
                else:
                    return Huobi.place_order(amount, price, "eosusdt", "sell-ioc")

        if operation == 'buy':
            new_currency_amount = float(self._redis.get('huobi_currency_amount')) + amount
            new_usdt_amount = float(self._redis.get('huobi_usdt_amount')) - amount * price
            if advance_mode:
                if new_currency_amount >= 0 and new_usdt_amount >= 0:
                    return True
                else: return None
            else:
                if self._redis.get('exec_mode') == b'simulation':
                    self._redis.set('huobi_currency_amount', new_currency_amount)
                    self._redis.set('huobi_usdt_amount', new_usdt_amount)
                    return True
                else:
                    return Huobi.place_order(amount, price, "eosusdt", "buy-ioc")

    def _binance_trade_handler(self, operation: str, price: float, amount: float, advance_mode=None):
        
        order_size = price * amount

        if order_size <= 10: return None

        if operation == 'sell':
            new_currency_amount = float(self._redis.get('binance_currency_amount')) - amount
            new_usdt_amount = float(self._redis.get('binance_usdt_amount')) + amount * price
            if advance_mode:
                if new_currency_amount >= 0 and new_usdt_amount >= 0:
                    return True
                else: return None
            else:
                if self._redis.get('exec_mode') == b'simulation':
                    self._redis.set('binance_currency_amount', new_currency_amount)
                    self._redis.set('binance_usdt_amount', new_usdt_amount)
                    return True
                else:
                    return Binance.place_order("eosusdt", "sell", "LIMIT", amount, price)

        if operation == 'buy':
            new_currency_amount = float(self._redis.get('binance_currency_amount')) + amount
            new_usdt_amount = float(self._redis.get('binance_usdt_amount')) - amount * price
            if advance_mode:
                if new_currency_amount >= 0 and new_usdt_amount >= 0:
                    return True
                else: return None
            else:
                if self._redis.get('exec_mode') == b'simulation':
                    self._redis.set('binance_currency_amount', new_currency_amount)
                    self._redis.set('binance_usdt_amount', new_usdt_amount)
                    return True
                else:
                    return Binance.place_order("eosusdt", "buy", "LIMIT", amount, price)
    
    def account_update(self):
        huobi_account = Huobi.get_account_balance(config['MODE']['currency_code'], "usdt")
        HUOBI_CURRENCY_AMOUNT = huobi_account['eos']['balance']
        HUOBI_USDT_AMOUNT = huobi_account['usdt']['balance']  
        
        binance_account = Binance.get_account_balance(config['MODE']['currency_code'], "usdt")
        BINANCE_CURRENCY_AMOUNT = binance_account['eos']['free']
        BINANCE_USDT_AMOUNT = binance_account['usdt']['free']

        redis.set('huobi_currency_amount', HUOBI_CURRENCY_AMOUNT)  
        redis.set('huobi_usdt_amount', HUOBI_USDT_AMOUNT)
        redis.set('binance_currency_amount', BINANCE_CURRENCY_AMOUNT)  
        redis.set('binance_usdt_amount', BINANCE_USDT_AMOUNT)

    def _get_max_trade_amount(self, margin: float):
        rules = self.trade_rule_json
        for label, rule in rules.items():
            if float(rule['from']) <= margin < float(rule['to']):
                return (label, rule['rate'], float(rule['rate']) * INIT_TOTAL_CURRENCY_AMOUNT)
        return (None, None, None)       

    def _print_on_terminal(self, *data, render_type='normal'):
        """[summary]
        
        Keyword Arguments:
            *data - the specific sub-parameters depend on the given render type
            render_type {str} -- [description] (default: {'normal'})
        """
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = '----------------------------------'+self.currency[1]+'------------------------------\r\n'+time

        self.logger.debug(title)

        if render_type == 'normal':
            
            a_record, b_record = data[0], data[1] 

            a_msg = '{} -> (max bid: {:.20f}, amount: {:.20f}); (min ask: {:.20f}, amount: {:.20f})'\
                    .format(str(a_record['market']), a_record['max_bid'], a_record['bid_amount'],\
                    a_record['min_ask'], a_record['ask_amount'])
            b_msg = '{} -> (max bid: {:.20f}, amount: {:.20f}), (min ask: {:.20f}, amount: {:.20f})'\
                    .format(str(b_record['market']), b_record['max_bid'], b_record['bid_amount'],\
                    b_record['min_ask'], b_record['ask_amount'])
            
            self.logger.debug(a_msg)
            self.logger.debug(b_msg)

        if render_type == 'trade_event':

            a_record, b_record, operable_amount = data[0], data[1],  data[2]    

            available_amount = min(float(a_record['bid_amount']), float(b_record['ask_amount']))
            msg = '\r\n>>>>>>>>>>>>>>>>>>>>>>Trade Event<<<<<<<<<<<<<<<<<<<<\r\n--->{} max bid: {:.20f} > {} min ask: {:.20f} --- available amount: {:.20f} --- operable amount: {:.20f}\r\n'.\
                        format(a_record['market'], float(a_record['max_bid']), b_record['market'], float(b_record['min_ask']), available_amount, operable_amount)
            self.logger.info(msg)

        if render_type == 'trade_rule':
            margin, rule_label, trade_rate = data[0], data[1], data[2]
            msg = '---> current margin: {}, applied trade rule: {} with rate: {}'.format(margin, rule_label, trade_rate )
            self.logger.info(msg)         

        if render_type == 'status':
            table = PrettyTable()
            table.field_names = ["Platforms", self.currency[0].upper(), "USDT"]
            if self._redis.get('exec_mode') == b'simulation':
                table.add_row(["HUOBI", round( float(self._redis.get('huobi_currency_amount')), 20), round( float(self._redis.get('huobi_usdt_amount')) , 20)])
                table.add_row(["BINANCE", round(float(self._redis.get('binance_currency_amount')), 20), round(float(self._redis.get('binance_usdt_amount')), 20)])
                self.logger.info("{}{}".format("\r\n", table))
                
                currency_profit = float(self._redis.get('huobi_currency_amount')) + float(self._redis.get('binance_currency_amount')) - INIT_TOTAL_CURRENCY_AMOUNT
                usdt_profit = float(self._redis.get('huobi_usdt_amount')) + float(self._redis.get('binance_usdt_amount')) - INIT_TOTAL_USDT_AMOUNT
                msg = '\r\n---> initial {} amount / profit: {} / {:.20f} <--- \r\n---> initial usdt amount / profit: {} / {:.20f} <---'.\
                    format(self.currency[0], INIT_TOTAL_CURRENCY_AMOUNT, currency_profit, INIT_TOTAL_USDT_AMOUNT, usdt_profit)
              
                self.logger.info(msg)
            else:
                self.logger.info('print for prod status')

        if render_type == 'trade_operation':

            operation = data[0]
            platform = data[1]
            operable_amount = data[2]

            if operation == 'sell':
                operation_total_price = float(platform['max_bid']) * float(operable_amount)
                msg = '---> {:.20f} {} were sold in {} with the price {:.20f} usdt <---'.format(operable_amount, self.currency[0].upper(), platform['market'], operation_total_price)
            elif operation == 'buy':
                operation_total_price = float(platform['min_ask']) * float(operable_amount)
                msg = '---> {:.20f} {} were purchased in {} with the price {:.20f} usdt <---'.format(operable_amount, self.currency[0].upper(), platform['market'], operation_total_price)
            self.logger.info(msg)

        if render_type == 'continue':

            platform = data[0]

            if platform:
                msg = '---> {} platform cannot confirm this trade, then breaking this transaction and waiting for the next <---'.format(platform)
            else:
                msg = '--->  this trade cannot be handled in terms of account balance, waiting for the next <---'

            self.logger.info(msg)
            self._print_on_terminal(None, None, None, render_type='status')