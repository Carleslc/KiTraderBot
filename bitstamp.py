# -*- coding: utf-8 -*-

import os, re
from account import Account
from json import loads as json
from requests import get
from pathlib import Path

BASE_URL = "https://www.bitstamp.net/api/v2"

FEE = 0.005
MIN_TRADE = 5

REQUESTS_LIMIT_PER_MINUTE = 60
REQUESTS_LIMIT_PER_SECOND = REQUESTS_LIMIT_PER_MINUTE // 60

ORDERS = set(['BUY', 'SELL'])

NON_ALPHA = r'[^a-zA-Z]'

try:
    with open("tokens/bitstamp", 'r') as bitstamp_token:
        BITSTAMP_API_TOKEN = bitstamp_token.read().strip()

    with open("tokens/bitstamp_secret", 'r') as bitstamp_secret:
        BITSTAMP_API_SECRET = bitstamp_secret.read().strip()
except FileNotFoundError:
    print("Bitstamp token not found")

ACCOUNTS = dict() # user to Account

def __get(url, callback, filter_status=True):
    response = get(BASE_URL + url)
    code = response.status_code
    if not filter_status:
      return callback(json(response.content), code)
    if code >= 200 and code < 300:
      return callback(json(response.content))
    return f"Bitstamp API: {code}"

def ping():
    return __get("/ticker/btcusd", lambda _: "Bitstamp API seems to be working.")

def __list_pairs(pairs):
    return '\n'.join(map(lambda pair: pair.get('name').replace('/', ''), pairs))

def list_symbols(user):
    def pairs_info(pairs):
        if existsAccount(user):
            currency = ACCOUNTS[user].currency
            my_pairs = list(filter(lambda pair: currency in pair.get('name').split('/'), pairs))
            others = filter(lambda pair: pair not in my_pairs, pairs)
            list_pairs_info = f"Available symbols for your account (Currency {currency}):\n\n"
            list_pairs_info += __list_pairs(my_pairs)
            list_pairs_info += "\n\nAvailable symbols in other currencies:\n\n"
            list_pairs_info += __list_pairs(others)
            return list_pairs_info.rstrip()
        return __list_pairs(pairs)
    return __get("/trading-pairs-info", pairs_info)

def __symbol(symbol):
    return re.sub(NON_ALPHA, '', symbol.lower())

def __price(symbol, callback):
    def parse(data, status_code):
        if status_code == 200:
            return callback(data.get('last'))
        return f"Invalid symbol: {symbol.upper()}. See /list"
    return __get("/ticker/" + __symbol(symbol), parse, filter_status=False)

def get_price(symbol):
    return __price(symbol, lambda price: float(price))

def price(user, symbol):
    if not symbol:
        currency = ACCOUNTS[user].currency if existsAccount(user) else 'USD'
        symbol = f'BTC{currency}'
    return __price(symbol, lambda current: f"{symbol.upper()}: {current}")

def exists(symbol):
    return __get("/ticker/" + __symbol(symbol), lambda _, status_code: status_code == 200, filter_status=False)

def is_authorized(bot_name, from_user, superuser, target):
    return target == from_user or (superuser and target == bot_name)

def account(bot_name, user, superuser, other):
    target = other if other != '' else user
    if not is_authorized(bot_name, user, superuser, target):
        return f"You are not allowed to view {target} account."
    if existsAccount(target):
        return str(ACCOUNTS[target])
    elif target == user:
        return "You do not have an account. /newAccount"
    return f"{target} do not have an account."

def history(bot_name, user, superuser, other):
    target = other if other != '' else user
    if not is_authorized(bot_name, user, superuser, target):
        return f"You are not allowed to view {target} trades."
    if existsAccount(target):
        return ACCOUNTS[target].history()
    elif target == user:
        return "You do not have an account. /newAccount"
    return f"{target} do not have an account."

def __float(s):
    try:
        return True, float(s)
    except ValueError:
        return False, 0

def existsAccount(user):
    return user in ACCOUNTS

def newAccount(user, args=''):
    args = args.split(' ', 1)
    balance = args[0] if args[0] else '1000'
    success, balance = __float(balance)
    if not success:
        return "Balance must be in decimal format. For example: 500.25 USD"
    currency = 'USD' if len(args) < 2 else args[1]
    account = Account(user, balance, currency, MIN_TRADE)
    ACCOUNTS[user] = account
    return f"Your account has been created successfully.\n\n{account}"

def deleteAccount(user):
    if not existsAccount(user):
        return "You do not have an account to delete."
    ACCOUNTS.pop(user)
    file = f"accounts/{user}"
    if os.path.exists(file):
        os.remove(file)
    return "Your account has been deleted."

def trade(user, order):
    if not existsAccount(user):
        return "You do not have an account. /newAccount"
    account = ACCOUNTS[user]
    args = order.split(' ', 3)
    action = args[0].upper()
    if len(args) < 3 or action not in ORDERS:
        return "Invalid order syntax: /trade [BUY, SELL] amount symbol [comment]"
    success, amount = __float(args[1])
    if not success:
        return "Amount must be in decimal format. For example: 1.5 ETH"
    symbol = args[2] + account.currency if account.currency not in args[2] else args[2]
    comment = ' '.join(args[3:]) if len(args) > 3 else ''
    if not exists(symbol):
        return f"Invalid symbol: {symbol.upper()}. See /list"
    symbol = __symbol(symbol)
    current = get_price(symbol)
    if action == 'BUY':
        return account.buy(symbol, current, amount, FEE, comment)
    elif action == 'SELL':
        return account.sell(symbol, current, amount, FEE, comment)

def tradeAll(user, order):
    if not existsAccount(user):
        return "You do not have an account. /newAccount"
    account = ACCOUNTS[user]
    args = order.split(' ', 2)
    action = args[0].upper()
    if len(args) < 2 or action not in ORDERS:
        return "Invalid order syntax: /tradeAll [BUY, SELL] symbol [comment]"
    symbol = args[1] + account.currency if account.currency not in args[1] else args[1]
    comment = ' '.join(args[2:]) if len(args) > 2 else ''
    if not exists(symbol):
        return f"Invalid symbol: {symbol.upper()}. See /list"
    symbol = __symbol(symbol)
    current = get_price(symbol)
    if action == 'BUY':
        return account.buy_all(symbol, current, FEE, comment)
    elif action == 'SELL':
        return account.sell_all(symbol, current, FEE, comment)

def load():
    Path('accounts').mkdir(parents=True, exist_ok=True)
    for user in os.listdir('accounts'):
        account = Account.load(f"accounts/{user}")
        ACCOUNTS[user] = account

def save():
    for account in ACCOUNTS.values():
        account.save(f"accounts/{account.user}")
