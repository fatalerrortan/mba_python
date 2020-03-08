import asyncio
from datetime import datetime
import time
import traceback
import json
from prettytable import PrettyTable
import configparser
import logging

class Core():
    def __init__(self, redis: object, currency: str, freq_analyser: object, huobi: object, binance: object):

        self.logger = logging.getLogger("root.{}".format(__name__))
        self._redis = redis
        self.currency = (currency, '{} / usdt'.format(currency).upper())# param0: currency code; param1: curreny / usdt
        self.currency_code = currency
        self.freq_analyser = freq_analyser
        self.trade_rule_json = self._get_trade_rules(currency)
        self.huobi = huobi
        self.binance = binance
        # self.show_off_account_status()

    async def bricks_checking(self):
        """[summary]
        # compare the records of selected platforms 
        """
        while True:
            await asyncio.sleep(1)

            try:
                huobi_record = json.loads(self._redis.get('huobi'))
                binance_record = json.loads(self._redis.get('binance'))
                self._print_on_terminal(huobi_record, binance_record, None, render_type='normal')
            except Exception as e:
                self.logger.warning("ERROR: cannot retrieve current bid and sell records from redis")
                self.logger.critical(getattr(e, 'message', repr(e)))
                self.logger.critical(traceback.format_exc())
                continue
            
            self._is_profitable(huobi_record, binance_record)
            self._is_profitable(binance_record, huobi_record)

    async def show_off_account_status(self):
        while True:
            await asyncio.sleep(180)
            self._print_on_terminal(None, None, None, render_type='status')

    def _is_profitable(self, a: json, b: json):
        """[summary]
        
        Arguments:
            a {json} -- [description]
            b {json} -- [description]
        """

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
                except Exception as e:
                    self.logger.critical("ERROR: cannot get max trade amount, it could be caused by reading undefined trade rule rules/testing.json")
                    self.logger.critical(getattr(e, 'message', repr(e)))
                    self.logger.critical(traceback.format_exc())
                    raise

                if MAX_TRADE_AMOUNT:
                    if available_trade_amount > MAX_TRADE_AMOUNT:
                        available_trade_amount = MAX_TRADE_AMOUNT
                        available_trade_amount = self.lot_size_validate(str(available_trade_amount))
            
                    try:
                        a_acceptable_amount = trade_handler[a_market]('sell', a_max_bid, available_trade_amount, advance_mode=True)
                        # get the adjusted new a_new_amount(could be unchanged) and then pass the a_new_amount to the followd checker, namely trade_handler[b_market]
                        if a_acceptable_amount:
                            a_acceptable_amount = self.lot_size_validate(str(a_acceptable_amount))
                            self._print_on_terminal(a, b, a_acceptable_amount, render_type='trade_event')
                            self._print_on_terminal(margin, rule_label, trade_rate, render_type='trade_rule')
                            b_acceptable_amount = trade_handler[b_market]('buy', b_min_ask, a_acceptable_amount, advance_mode=True)
                            
                    except Exception as e:
                        self.logger.critical("ERROR: transaction pre check mode failed")
                        self.logger.critical(getattr(e, 'message', repr(e)))
                        self.logger.critical(traceback.format_exc())
                        raise   

                    if a_acceptable_amount and b_acceptable_amount:

                        print("amount_a: "+str(a_acceptable_amount))
                        print("amount_b: "+str(b_acceptable_amount))
                        
                        a_sell_result = trade_handler[a_market]('sell', a_max_bid, a_acceptable_amount)
                        if a_sell_result:
                            self._print_on_terminal('sell', a, a_acceptable_amount, render_type='trade_operation')
                            b_buy_result = trade_handler[b_market]('buy', b_min_ask, b_acceptable_amount)
                            if b_buy_result:
                                self._print_on_terminal('buy', b, b_acceptable_amount, render_type='trade_operation')
                            else:
                                self._print_on_terminal(b_market, None, None, render_type='continue')
                            try:
                                if not self._redis.get('exec_mode') == b'simulation':
                                    self.account_update()
                            except Exception as e:
                                self.logger.critical("ERROR: ERROR: cannot update accout balance after transaction")
                                self.logger.critical(getattr(e, 'message', repr(e)))
                                self.logger.critical(traceback.format_exc())
                                raise
                            self._print_on_terminal(None, None, None, render_type='status') 
                        else:
                            self._print_on_terminal(a_market, None, None, render_type='continue')                                 
                    else:
                        self._print_on_terminal(None, None, None, render_type='continue')                      

    def _get_trade_rate(self, market):
        return 0
    
    def _get_trade_rules(self, currency):
        """[summary]
        
        Arguments:
            currency {[type]} -- [description]
        
        Returns:
            [type] -- [description]
        """
        TRADE_RULE_FILE = self._redis.get("trade_rule_file").decode("utf-8")
        with open('rules/{}'.format(TRADE_RULE_FILE)) as trade_rule_file:
            try:
                trade_rule_json = json.load(trade_rule_file)[currency] 
            except KeyError:
                self.logger.warning('ERROR: cannot find pre-defined trade rule, using default')    
                return self._get_trade_rules('default')
            return trade_rule_json    

    def _huobi_trade_handler(self, operation: str, price: float, amount: float, advance_mode=None):
        """[summary]
        
        Arguments:
            operation {str} -- [description]
            price {float} -- [description]
            amount {float} -- [description]
        
        Keyword Arguments:
            advance_mode {[type]} -- [description] (default: {None})
        
        Returns:
            [type] -- [description]
        """
        order_size = price * amount

        if order_size <= 10: return None

        if operation == 'sell':
            new_currency_amount = float(self._redis.get('huobi_currency_amount')) - amount
            new_usdt_amount = float(self._redis.get('huobi_usdt_amount')) + amount * price
            if advance_mode:
                if new_currency_amount >= 0 and new_usdt_amount >= 0:
                    return amount
                else: 
                    new_order_size = price * float(self._redis.get('huobi_currency_amount'))
                    if new_order_size <= 10:
                        return None
                    else: return float(self._redis.get('huobi_currency_amount'))
            else:
                if self._redis.get('exec_mode') == b'simulation':
                    self._redis.set('huobi_currency_amount', new_currency_amount)
                    self._redis.set('huobi_usdt_amount', new_usdt_amount)
                    return True
                else:
                    order_id = self.huobi.place_order(amount, price, self.currency_code+"usdt", "sell-limit")
                    if not order_id: return None
                    
                    time.sleep(0.5)
                    order_status = self.huobi.get_order_detail(order_id)
                    if order_status == "filled":
                        return amount
                    else: 
                        if self.huobi.cancel_order(order_id) == "ok":
                            return None
                        
        if operation == 'buy':
            new_currency_amount = float(self._redis.get('huobi_currency_amount')) + amount
            new_usdt_amount = float(self._redis.get('huobi_usdt_amount')) - amount * price
            if advance_mode:
                if new_currency_amount >= 0 and new_usdt_amount >= 0:
                    return amount
                else: 
                    return None
            else:
                if self._redis.get('exec_mode') == b'simulation':
                    self._redis.set('huobi_currency_amount', new_currency_amount)
                    self._redis.set('huobi_usdt_amount', new_usdt_amount)
                    return True
                else:
                    order_id = self.huobi.place_order(amount, price, self.currency_code+"usdt", "buy-limit")
                    retry = 0
                    while retry < 33:
                        time.sleep(1)
                        order_status = self.huobi.get_order_detail(order_id)
                        if order_status == "filled":
                            return amount
                        retry += 1
                    
                    if self.huobi.cancel_order(order_id) == "ok":
                        return self.huobi.place_order(amount, 0, self.currency_code+"usdt", "buy-market")
                        

    def _binance_trade_handler(self, operation: str, price: float, amount: float, advance_mode=None):
        """[summary]
        
        Arguments:
            operation {str} -- [description]
            price {float} -- [description]
            amount {float} -- [description]
        
        Keyword Arguments:
            advance_mode {[type]} -- [description] (default: {None})
        
        Returns:
            [type] -- [description]
        """
        
        order_size = price * amount

        if order_size <= 10: return None

        if operation == 'sell':
            new_currency_amount = float(self._redis.get('binance_currency_amount')) - amount
            new_usdt_amount = float(self._redis.get('binance_usdt_amount')) + amount * price
            if advance_mode:
                if new_currency_amount >= 0 and new_usdt_amount >= 0:
                    return amount
                else: 
                    new_order_size = price * float(self._redis.get('binance_currency_amount'))
                    if new_order_size <= 10:
                        return None
                    else: return float(self._redis.get('binance_currency_amount'))                
            else:
                if self._redis.get('exec_mode') == b'simulation':
                    self._redis.set('binance_currency_amount', new_currency_amount)
                    self._redis.set('binance_usdt_amount', new_usdt_amount)
                    return True
                else:
                    result = self.binance.place_order(self.currency_code+"usdt", "sell", "LIMIT", amount, price, "FOK")
                    if result["status"] == "FILLED":
                        return amount
                    return None

        if operation == 'buy':
            new_currency_amount = float(self._redis.get('binance_currency_amount')) + amount
            new_usdt_amount = float(self._redis.get('binance_usdt_amount')) - amount * price
            if advance_mode:
                if new_currency_amount >= 0 and new_usdt_amount >= 0:
                    return amount
                else: return None
            else:
                if self._redis.get('exec_mode') == b'simulation':
                    self._redis.set('binance_currency_amount', new_currency_amount)
                    self._redis.set('binance_usdt_amount', new_usdt_amount)
                    return True
                else:
                    result = self.binance.place_order(self.currency_code+"usdt", "buy", "LIMIT", amount, price, "GTC")
                    if result["status"] == "FILLED":
                        return amount
                    elif result["status"] == "NEW":
                        retry = 0
                        while retry < 33:
                            time.sleep(1)
                            order_status = self.binance.get_order_detail(self.currency_code+"usdt", result["orderId"])["status"]
                            if order_status == "FILLED":
                                return amount
                            retry += 1

                        order_status = self.binance.cancel_order(self.currency_code+"usdt", result["orderId"])["status"]
                        if order_status == "CANCELED":
                            return self.binance.place_order(self.currency_code+"usdt", "buy", "market", amount, 0, "GTC")
                    else: return None
                        
    def account_update(self):
       
        huobi_account = self.huobi.get_account_balance(self.currency_code, "usdt")
        HUOBI_CURRENCY_AMOUNT = huobi_account[self.currency_code]['balance']
        HUOBI_USDT_AMOUNT = huobi_account['usdt']['balance']  
        
        binance_account = self.binance.get_account_balance(self.currency_code, "usdt")
        BINANCE_CURRENCY_AMOUNT = binance_account[self.currency_code]['free']
        BINANCE_USDT_AMOUNT = binance_account['usdt']['free']

        self._redis.set('huobi_currency_amount', HUOBI_CURRENCY_AMOUNT)  
        self._redis.set('huobi_usdt_amount', HUOBI_USDT_AMOUNT)
        self._redis.set('binance_currency_amount', BINANCE_CURRENCY_AMOUNT)  
        self._redis.set('binance_usdt_amount', BINANCE_USDT_AMOUNT)

    def _get_max_trade_amount(self, margin: float):
        """[summary]
        
        Arguments:
            margin {float} -- [description]
        
        Returns:
            [type] -- [description]
        """
        rules = self.trade_rule_json
        current_total_curreny_amount = float(self._redis.get('huobi_currency_amount'))+ float(self._redis.get('binance_currency_amount'))
        for label, rule in rules.items():
            if float(rule['from']) <= margin < float(rule['to']):
                return (label, rule['rate'], float(rule['rate']) * current_total_curreny_amount)
        return (None, None, None)             
    
    def lot_size_validate(self, number: str):
        """[summary]
        
        Arguments:
            number {[type]} -- [description]
        
        Keyword Arguments:
            precision {int} -- [description] (default: {2}) binance eos default lotsize
        
        Returns:
            [type] -- [description]
        """
        
        precision = int(self._redis.get("amount_precision"))

        numbers = str(number)
        if "." in numbers:
            numbers = str(number).split(".")
            number_strfy = numbers[0] + "." + numbers[1][:precision]
            
            return float(number_strfy)
        else: return float(numbers)

    def _print_on_terminal(self, *data, render_type='normal'):
        """[summary]
        
        Keyword Arguments:
            *data - the specific sub-parameters depend on the given render type
            render_type {str} -- [description] (default: {'normal'})
        """
        # time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = '----------------------------------'+self.currency[1]+'------------------------------\r\n'

        self.logger.debug(title)

        if render_type == 'normal':
            
            a_record, b_record = data[0], data[1] 

            a_msg = '{} -> (max bid: {}, amount: {}); (min ask: {}, amount: {})'\
                    .format(str(a_record['market']), a_record['max_bid'], self.lot_size_validate(str(a_record['bid_amount'])),\
                    a_record['min_ask'], self.lot_size_validate(str(a_record['ask_amount'])))
            b_msg = '{} -> (max bid: {}, amount: {}), (min ask: {}, amount: {})'\
                    .format(str(b_record['market']), b_record['max_bid'], self.lot_size_validate(str(b_record['bid_amount'])),\
                    b_record['min_ask'], self.lot_size_validate(str(b_record['ask_amount'])))
            
            self.logger.debug(a_msg)
            self.logger.debug(b_msg)

        if render_type == 'trade_event':

            a_record, b_record, operable_amount = data[0], data[1],  data[2]    

            available_amount = min(float(a_record['bid_amount']), float(b_record['ask_amount']))
            msg = '\r\n>>>>>>>>>>>>>>>>>>>>>>Trade Event<<<<<<<<<<<<<<<<<<<<\r\n--->{} max bid: {} > {} min ask: {} --- available amount: {} --- operable amount: {}\r\n'.\
                        format(a_record['market'], float(a_record['max_bid']), b_record['market'], float(b_record['min_ask']), self.lot_size_validate(str(available_amount)), self.lot_size_validate(str(operable_amount)))
            self.logger.info(msg)

        if render_type == 'trade_rule':
            margin, rule_label, trade_rate = data[0], data[1], data[2]
            msg = '---> current margin: {}, applied trade rule: {} with rate: {}'.format(margin, rule_label, trade_rate )
            self.logger.info(msg)         

        if render_type == 'status':
            table = PrettyTable()
            table.field_names = ["Platforms", self.currency[0].upper(), "USDT"]
            table.add_row(["HUOBI", self._redis.get('huobi_currency_amount').decode("utf-8"), self._redis.get('huobi_usdt_amount').decode("utf-8")])
            table.add_row(["BINANCE", self._redis.get('binance_currency_amount').decode("utf-8"), self._redis.get('binance_usdt_amount').decode("utf-8")])
            self.logger.info("{}{}".format("\r\n", table))
            
            currency_profit = round(float(self._redis.get('huobi_currency_amount')) + float(self._redis.get('binance_currency_amount')) - float(self._redis.get("init_total_curreny_amount")), 5)
            usdt_profit = round(float(self._redis.get('huobi_usdt_amount')) + float(self._redis.get('binance_usdt_amount')) - float(self._redis.get("init_total_usdt_amount")), 5)
            msg = '\r\n---> initial {} amount / profit: {} / {} <--- \r\n---> initial usdt amount / profit: {} / {} <---'.\
                format(self.currency[0], self._redis.get("init_total_curreny_amount").decode("utf-8"), currency_profit, self._redis.get("init_total_usdt_amount").decode("utf-8"), usdt_profit)
            
            self.logger.info(msg)


        if render_type == 'trade_operation':

            operation = data[0]
            platform = data[1]
            operable_amount = data[2]

            if operation == 'sell':
                operation_total_price = float(platform['max_bid']) * float(operable_amount)
                msg = '---> {} {} were sold in {} with the price {} usdt <---'.format(operable_amount, self.currency[0].upper(), platform['market'], operation_total_price)
            elif operation == 'buy':
                operation_total_price = float(platform['min_ask']) * float(operable_amount)
                msg = '---> {} {} were purchased in {} with the price {} usdt <---'.format(operable_amount, self.currency[0].upper(), platform['market'], operation_total_price)
            self.logger.info(msg)

        if render_type == 'continue':

            platform = data[0]

            if platform:
                msg = '---> {} platform cannot confirm this trade, then breaking this transaction and waiting for the next <---'.format(platform)
            else:
                msg = '--->  this trade cannot be handled in terms of account balance, waiting for the next <---'

            self.logger.info(msg)
            self._print_on_terminal(None, None, None, render_type='status')