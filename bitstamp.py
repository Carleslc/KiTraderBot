from json import loads as json
from requests import get

BASE_URL = "https://www.bitstamp.net/api/v2"

FEE = 0.0025
BALANCE = 50
MIN_TRADE = 5

REQUESTS_LIMIT_PER_MINUTE = 60
REQUESTS_LIMIT_PER_SECOND = REQUESTS_LIMIT_PER_MINUTE // 60

with open("tokens/bitstamp", 'r') as bitstamp_token:
    BINANCE_API_TOKEN = bitstamp_token.read()

with open("tokens/bitstamp_secret", 'r') as bitstamp_secret:
    BINANCE_API_SECRET = bitstamp_secret.read()

SUBSCRIPTION_UPDATE_SECONDS = 10
SUBSCRIBERS = dict() # users to (symbol, balance, open, open amount, stop profit price, stop loss price)

def __get(url, callback):
    response = get(BASE_URL + url)
    code = response.status_code
    if code >= 200 and code < 300:
        return callback(json(response.content))
    else:
        return f"Cannot connect to Bitstamp API: {code}"

def ping():
    return __get("/ticker/btcusd", lambda _: "Bitstamp API seems to be working.")

def __price(symbol, callback):
    return __get("/ticker/" + symbol.lower(), lambda data: callback(data.get('last')))

def price(symbol):
    if not symbol:
        symbol = "btcusd"
    return __price(symbol, lambda current: f"{symbol.upper()}: {current}")

def __exists(symbol):
    return get(BASE_URL + "/ticker/" + symbol).status_code == 200

def subscription_update(user):
    return autotrade(user) if user in SUBSCRIBERS else "Unsubscribed."

def subscribe(user, symbol):
    symbol = symbol.lower()
    if len(SUBSCRIBERS) >= SUBSCRIPTION_UPDATE_SECONDS * REQUESTS_LIMIT_PER_SECOND:
        return -1, f"Sorry, cannot subscribe. Maximum subscriptors reached: {len(SUBSCRIBERS)}"
    if not __exists(symbol):
        return -1, "Invalid symbol."
    SUBSCRIBERS[user] = (symbol, BALANCE, None, None, None, None)
    return SUBSCRIPTION_UPDATE_SECONDS, f"Now you're subscribed to {symbol.upper()}, updated every minute."

def unsubscribe(user):
    if user not in SUBSCRIBERS:
        return "Already unsubscribed."
    SUBSCRIBERS.pop(user)
    return "Unsubscribed successfully."

def autotrade(user):
    (symbol, balance, open, amount, stop_profit, stop_loss) = SUBSCRIBERS[user]
    current = __price(symbol, lambda price: float(price))
    if open is None:
        if balance <= MIN_TRADE:
            return f"Insufficient balance: {balance}"
        amount = min(balance, BALANCE) / current
        open = amount * current
        open_fee = FEE * open
        open = open - open_fee
        amount = open / current
        balance = balance - open - open_fee
        benefits_percent = 2 / 100
        stop_percent = benefits_percent / 2
        target = open + open_fee + ((open + open_fee) * benefits_percent)
        close_fee = FEE * target
        stop_profit = (target + close_fee) / amount
        stop_loss = (open - ((open + open_fee) * stop_percent)) / amount
        SUBSCRIBERS[user] = (symbol, balance, open, amount, stop_profit, stop_loss)
        return f"BUY {amount} {symbol} at {current} for {open} with {open_fee} fees.\nTarget: {stop_profit}\nStop Loss: {stop_loss}\nBalance: {balance}"
    elif current >= stop_profit:
        close = amount * current
        close_fee = FEE * close
        close = close - close_fee
        balance = balance + close
        SUBSCRIBERS[user] = (symbol, balance, None, None, None, None)
        return f"SELL {amount} {symbol} at {current} for {close} with {close_fee} fees.\nBalance: {balance}\nReturn: {(balance / BALANCE - 1) * 100}%"
    elif current <= stop_loss:
        close = amount * current
        close_fee = FEE * close
        close = close - close_fee
        balance = balance + close
        SUBSCRIBERS[user] = (symbol, balance, None, None, None, None)
        return f"STOP LOSS {amount} {symbol} at {current} for {close} with {close_fee} fees.\nBalance: {balance}\nReturn: {(balance / BALANCE - 1) * 100}%"