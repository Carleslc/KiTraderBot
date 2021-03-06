# KiTraderBot
Trading bot simulator for Telegram. Supports Bitstamp & Binance APIs.

[![ko-fi](https://www.ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/carleslc)

## Commands

```
/start - Shows this message
/ping - Test connection with trading API
/list - Show the available symbols
/price symbol - Current price for provided symbol
/account [KiTrader, Carleslc] - View your account or the bot account
/newAccount [balance] [currency] - Creates an account for trading
/deleteAccount - Deletes your trading account
/history [KiTrader, Carleslc] - View your trades or the bot trades
/trade [BUY, SELL] amount symbol [comment] - Order a trade for your account
/tradeAll [BUY, SELL] symbol [comment] - Order a trade for your account with maximum available amount
/subscribe - Receive updates from the KiTrader auto-trading account
/update - Forces an update of the KiTrader auto-trading subscription
/unsubscribe - Stop receiving updates from the KiTrader auto-trading account
```

## Install

#### Dependencies

https://python-telegram-bot.org/

```bash
python3 -m pip install -r dependencies.txt
```

#### Telegram

Create your bot and get an Access Token with https://core.telegram.org/bots#6-botfather

Create a new folder **`tokens`**

Create a new file **`tokens/telegram`** and paste your bot token there.

#### Bitstamp

Get API key and secret from https://www.bitstamp.net/account/security/api/

**`tokens/bitstamp`**

**`tokens/bitstamp_secret`**

#### Binance

Change `import bitstamp as trading` to `import binance as trading` in `bot.py` and `account.py`.

Get API key and secret from https://www.binance.com/en/usercenter/settings/api-management

**`tokens/binance`**

**`tokens/binance_secret`**

#### Allow users to subscription / trading

Create a file **`users`** and enter each user in a new line for granting permissions.

#### Read alerts from Gmail

This bot can read alerts from email and put buy/sell orders in a simulated account for testing strategies.

Update `gmail.py` constants to identify alerts.

Read header and use `oauth2.py` to get your token credentials.

**`tokens/gmail_at`** your email address

**`tokens/gmail`** token credentials

### Deploy

#### Run

```bash
python3 bot.py
```

#### Docker

```bash
docker build -t kitraderbot .
docker-compose up -d

# Update (after build)
docker-compose restart kitraderbot

# Update (single line rebuild)
docker-compose up --build --force-recreate --no-deps -d kitraderbot
```
