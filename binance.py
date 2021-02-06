# -*- coding: utf-8 -*-

from json import loads as json
from requests import get

BASE_URL = "https://api.binance.com"

REQUESTS_LIMIT_PER_MINUTE = 1200
REQUESTS_LIMIT_PER_SECOND = REQUESTS_LIMIT_PER_MINUTE // 60

try:
    with open("tokens/binance", 'r') as binance_token:
        BINANCE_API_TOKEN = binance_token.read().strip()

    with open("tokens/binance_secret", 'r') as binance_secret:
        BINANCE_API_SECRET = binance_secret.read().strip()
except FileNotFoundError:
    print("Binance token not found")

SUBSCRIPTION_UPDATE_SECONDS = 60
SUBSCRIBERS = dict() # users to symbol

def __get(url, callback):
    response = get(BASE_URL + url)
    code = response.status_code
    if code >= 200 and code < 300:
        return callback(json(response.content))
    elif code >= 400 and code < 500:
        return json(response.content).get('msg')
    else:
        return f"Cannot connect to Binance API: {code}"

def ping():
    return __get("/api/v1/ping", lambda _: "Binance API seems to be working.")

def price(symbol):
    symbol = symbol.upper()
    return __get("/api/v3/ticker/price?symbol=" + symbol, lambda data: f"{symbol}: {data.get('price')}")

def __exists(symbol):
    return get(BASE_URL + "/api/v3/ticker/price?symbol=" + symbol).status_code == 200

def subscription_update(user):
    return price(SUBSCRIBERS[user]) if user in SUBSCRIBERS else "Unsubscribed."

def subscribe(user, symbol):
    symbol = symbol.upper()
    if len(SUBSCRIBERS) >= SUBSCRIPTION_UPDATE_SECONDS * REQUESTS_LIMIT_PER_SECOND:
        return -1, f"Sorry, cannot subscribe. Maximum subscriptors reached."
    if not __exists(symbol):
        return -1, "Invalid symbol."
    SUBSCRIBERS[user] = symbol
    return SUBSCRIPTION_UPDATE_SECONDS, f"Now you're subscribed to {symbol}, updated every minute."

def unsubscribe(user):
    if user not in SUBSCRIBERS:
        return "Already unsubscribed."
    SUBSCRIBERS.pop(user)
    return "Unsubscribed successfully."
