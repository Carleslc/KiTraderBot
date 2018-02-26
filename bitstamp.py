import os
from account import *
from json import loads as json
from requests import get

BASE_URL = "https://www.bitstamp.net/api/v2"

FEE = 0.0025
MIN_TRADE = 5

REQUESTS_LIMIT_PER_MINUTE = 60
REQUESTS_LIMIT_PER_SECOND = REQUESTS_LIMIT_PER_MINUTE // 60

ORDERS = set(['BUY', 'SELL'])

with open("tokens/bitstamp", 'r') as bitstamp_token:
    BINANCE_API_TOKEN = bitstamp_token.read().strip()

with open("tokens/bitstamp_secret", 'r') as bitstamp_secret:
    BINANCE_API_SECRET = bitstamp_secret.read().strip()

SUBSCRIBERS = dict() # user to Account

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

def account(user, other):
    user = other if other != '' else user
    return str(SUBSCRIBERS[user]) if user in SUBSCRIBERS else f"{user} do not have any account."

def historic(user, other):
    user = other if other != '' else user
    return SUBSCRIBERS[user].history() if user in SUBSCRIBERS else f"{user} do not have any account."

def __float(s):
    try:
        return True, float(s)
    except ValueError:
        return False, 0

def subscribe(user, args):
    args = args.split(' ', 1)
    balance = args[0] if args[0] else '10000'
    (success, balance) = __float(balance)
    if not success:
        return 0, "Balance must be in decimal format. For example: 500.25"
    currency = 'USD' if len(args) < 2 else args[1]
    account = Account(user, balance, currency, MIN_TRADE)
    SUBSCRIBERS[user] = account
    return 0, f"Your account was created successfully.\n\n{account}"

def unsubscribe(user):
    if user not in SUBSCRIBERS:
        return "You do not have any account to delete."
    SUBSCRIBERS.pop(user)
    return "Your account has been deleted."

def __parse_args(args, length):
    return args.replace('Alerta de TradingView: ', '', 1).split(' ', length)

def trade(user, order):
    if user not in SUBSCRIBERS:
        return "You do not have any account."
    account = SUBSCRIBERS[user]
    args = __parse_args(order, 3)
    action = args[0].upper()
    if len(args) < 3 or action not in ORDERS:
        return "Invalid order syntax."
    (success, amount) = __float(args[1])
    if not success:
        return "Amount must be in decimal format. For example: 500.25"
    symbol = args[2] + account.currency if account.currency not in args[2] else args[2]
    comment = args[3] if len(args) > 3 else ''
    if not __exists(symbol):
        return f"Invalid symbol: {symbol.upper()}"
    current = get_price(symbol)
    if action == 'BUY':
        return account.buy(symbol, current, amount, FEE, comment)
    elif action == 'SELL':
        return account.sell(symbol, current, amount, FEE, comment)

def tradeAll(user, order):
    if user not in SUBSCRIBERS:
        return "You do not have any account."
    account = SUBSCRIBERS[user]
    args = __parse_args(order, 4)
    action = args[0].upper()
    if len(args) < 2 or action not in ORDERS:
        return "Invalid order syntax."
    symbol = args[1] + account.currency if account.currency not in args[1] else args[1]
    comment = args[2] if len(args) > 2 else ''
    if not __exists(symbol):
        return f"Invalid symbol: {symbol.upper()}"
    current = get_price(symbol)
    if action == 'BUY':
        return account.buy_all(symbol, current, FEE, comment)
    elif action == 'SELL':
        return account.sell_all(symbol, current, FEE, comment)

def load():
    for user in os.listdir('accounts'):
        account = Account.load('accounts/' + user)
        SUBSCRIBERS[user] = account

def save():
    for account in SUBSCRIBERS.values():
        account.save(f"accounts/{account.user}")