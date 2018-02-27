# -*- coding: utf-8 -*-

import json
from datetime import datetime

DECIMALS = 7

class Position:

    def __init__(self, symbol, amount):
        self.symbol = symbol
        self.amount = amount

    def __repr__(self):
        return f"{self.symbol}: {round(self.amount, DECIMALS)}"

class Account:

    def __init__(self, user, balance, currency, min_trade):
        self.user = user
        self.balance = balance
        self.currency = currency.upper()
        self.initial_balance = balance
        self.min_trade = max(0, min_trade)
        self.historic = list()
        self.positions = dict() # SYMBOL to Position

    def __str__(self):
        positions = '\nPositions:\n' + '\n'.join(map(lambda p: '\t- ' + str(p), self.positions.values())) if len(self.positions) > 0 else ''
        ret = Account.percent(self.balance / self.initial_balance)
        return f"User: {self.user}\nBalance: {self.__price(self.balance)}\nEquity: {self.__price(self.equity())}\nReturn: {round(ret, 3)}%{positions}"

    def load(file):
        with open(file, 'r') as account_file:
            return json.load(account_file, cls=Decoder)

    def save(self, file):
        with open(file, 'w') as account_file:
            json.dump(self, account_file, default=dumper)

    def percent(d):
        return (d - 1) * 100

    def __symbol(self, symbol):
        return symbol.upper().replace(self.currency, '', 1)

    def get(self, symbol):
        symbol = self.__symbol(symbol)
        return self.positions[symbol].amount if symbol in self.positions else 0.0

    def history(self):
        return '\n\n'.join(self.historic) if len(self.historic) > 0 else "No trades found."

    def now():
        return datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    def __price(self, p):
        return f"{round(p, 2)} {self.currency}"

    def __record(self, action, symbol, amount, price, cost, fee, comment):
        record = Account.now()
        icon = '📈' if action == 'BUY' else '📉'
        record += f"\n{icon} {action} {round(amount, DECIMALS)} {symbol} at {self.__price(price)} for {self.__price(cost)} with {self.__price(fee)} fees."
        record += f"\nEquity: {self.__price(self.equity())}"
        record += f"\nComment: {comment}" if comment else ''
        self.historic.append(record)
        return record

    def equity(self):
        from bitstamp import get_price
        return self.balance + sum(list(map(lambda p: p.amount * get_price(p.symbol + self.currency), self.positions.values())))

    def buy(self, symbol, current, amount, fee, comment=''):
        if self.balance <= 0:
            return f"Insufficient balance: {self.__price(self.balance)}."
        symbol = self.__symbol(symbol)
        open = amount * current
        if open < self.min_trade:
            return f"Trade price must be greater than {self.__price(self.min_trade)}. Current is {self.__price(open)} ({round(amount, DECIMALS)} {symbol} * {self.__price(current)})."
        maximum = self.balance / current
        if amount > maximum:
            return f"Invalid amount, your balance is {self.__price(self.balance)}. Maximum: {round(maximum, DECIMALS)} {symbol} at price {self.__price(current)}."
        open_fee = fee * open
        open = open - open_fee
        amount = open / current
        self.balance = self.balance - open - open_fee
        position = Position(symbol, amount)
        self.positions[symbol] = position
        return self.__record('BUY', symbol, amount, current, open, open_fee, comment)

    def buy_all(self, symbol, current, fee, comment=''):
        if self.balance <= 0:
            return f"Insufficient balance: {self.__price(self.balance)}."
        return self.buy(symbol, current, self.balance / current, fee, comment)

    def sell(self, symbol, current, amount, fee, comment=''):
        symbol = self.__symbol(symbol)
        close = amount * current
        if close < self.min_trade:
            return f"Trade price must be greater than {self.__price(self.min_trade)}. Current is {self.__price(close)} ({round(amount, DECIMALS)} {symbol} * {self.__price(current)})."
        total_amount = self.get(symbol)
        if amount > total_amount:
            return f"Invalid amount: {round(amount, DECIMALS)} {symbol}. Available: {round(total_amount, DECIMALS)} {symbol}."
        elif amount < total_amount:
            position = self.positions[symbol]
            position.amount = position.amount - amount
        else:
            self.positions.pop(symbol)
        close_fee = fee * close
        close = close - close_fee
        self.balance = self.balance + close
        return self.__record('SELL', symbol, amount, current, close, close_fee, comment)

    def sell_all(self, symbol, current, fee, comment=''):
        amount = self.get(symbol)
        if amount == 0:
            return f"There is no position open for {self.__symbol(symbol)}."
        return self.sell(symbol, current, amount, fee, comment)

def dumper(obj):
    try:
        return obj.toJSON()
    except:
        return obj.__dict__

class Decoder(json.JSONDecoder):
    def decode(self, s):
        d = super(Decoder, self).decode(s)
        account = Account(d['user'], d['balance'], d['currency'], d['min_trade'])
        account.initial_balance = d['initial_balance']
        account.historic = d['historic']
        positions = dict()
        for symbol, pos in d['positions'].items():
            positions[symbol] = Position(symbol, pos['amount'])
        account.positions = positions
        return account