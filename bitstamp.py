# -*- coding: utf-8 -*-

import os
from account import *
from json import loads as json
from requests import get
from pathlib import Path

BASE_URL = "https://www.bitstamp.net/api/v2"

FEE = 0.005
MIN_TRADE = 5

REQUESTS_LIMIT_PER_MINUTE = 60
REQUESTS_LIMIT_PER_SECOND = REQUESTS_LIMIT_PER_MINUTE // 60

ORDERS = set(['BUY', 'SELL'])

try:
    with open("tokens/bitstamp", 'r') as bitstamp_token:
        BITSTAMP_API_TOKEN = bitstamp_token.read().strip()

    with open("tokens/bitstamp_secret", 'r') as bitstamp_secret:
        BITSTAMP_API_SECRET = bitstamp_secret.read().strip()
except FileNotFoundError:
    print("Bitstamp token not found")

ACCOUNTS = dict() # user to Account

def __get(url, callback):
    response = get(BASE_URL + url)
    code = response.status_code
    if code >= 200 and code < 300:
        return callback(json(response.content))
    else:
        return f"Cannot connect to Bitstamp API: {code}"

def ping(user):
    return __get("/ticker/btcusd", lambda _: "Bitstamp API seems to be working.")

def __price(symbol, callback):
    return __get("/ticker/" + symbol.lower(), lambda data: callback(data.get('last')))

def get_price(symbol):
    return __price(symbol, lambda price: float(price))

def price(user, symbol):
    if not symbol:
        symbol = 'BTCUSD'
    return __price(symbol, lambda current: f"{symbol.upper()}: {current}")

def __exists(symbol):
    return get(BASE_URL + "/ticker/" + symbol.lower()).status_code == 200

def __authorized(bot_name, from_user, target):
    return target == from_user or target == bot_name

def account(bot_name, user, other):
    target = other if other != '' else user
    if not __authorized(bot_name, user, target):
        return f"You are not allowed to view {target} account."
    return str(ACCOUNTS[target]) if target in ACCOUNTS else f"{target} do not have any account."

def history(bot_name, user, other):
    target = other if other != '' else user
    if not __authorized(bot_name, user, target):
        return f"You are not allowed to view {target} trades."
    return ACCOUNTS[target].history() if target in ACCOUNTS else f"{target} do not have any account."

def __float(s):
    try:
        return True, float(s)
    except ValueError:
        return False, 0

def existsAccount(user):
    return user in ACCOUNTS

def newAccount(user, args=''):
    args = args.split(' ', 1)
    balance = args[0] if args[0] else '10000'
    success, balance = __float(balance)
    if not success:
        return "Balance must be in decimal format. For example: 500.25"
    currency = 'USD' if len(args) < 2 else args[1]
    account = Account(user, balance, currency, MIN_TRADE)
    ACCOUNTS[user] = account
    return f"Your account was created successfully.\n\n{account}"

def deleteAccount(user):
    if user not in ACCOUNTS:
        return "You do not have any account to delete."
    ACCOUNTS.pop(user)
    return "Your account has been deleted."

def trade(user, order):
    if user not in ACCOUNTS:
        return "You do not have any account."
    account = ACCOUNTS[user]
    args = order.split(' ', 3)
    action = args[0].upper()
    if len(args) < 3 or action not in ORDERS:
        return "Invalid order syntax."
    (success, amount) = __float(args[1])
    if not success:
        return "Amount must be in decimal format. For example: 500.25"
    symbol = args[2] + account.currency if account.currency not in args[2] else args[2]
    comment = ' '.join(args[3:]) if len(args) > 3 else ''
    if not __exists(symbol):
        return f"Invalid symbol: {symbol.upper()}"
    current = get_price(symbol)
    if action == 'BUY':
        return account.buy(symbol, current, amount, FEE, comment)
    elif action == 'SELL':
        return account.sell(symbol, current, amount, FEE, comment)

def tradeAll(user, order):
    if user not in ACCOUNTS:
        return "You do not have any account."
    account = ACCOUNTS[user]
    args = order.split(' ', 2)
    action = args[0].upper()
    if len(args) < 2 or action not in ORDERS:
        return "Invalid order syntax."
    symbol = args[1] + account.currency if account.currency not in args[1] else args[1]
    comment = ' '.join(args[2:]) if len(args) > 2 else ''
    if not __exists(symbol):
        return f"Invalid symbol: {symbol.upper()}"
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