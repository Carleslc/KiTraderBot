# KiTraderBot
Trading bot simulator for Telegram. Supports Bitstamp & Binance APIs.

[![ko-fi](https://www.ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/carleslc)

## Install

#### Dependencies

https://python-telegram-bot.org/

```bash
pip3 install python-telegram-bot pytz pycryptodome
```

#### Bitstamp

Get API key and secret from https://www.bitstamp.net/account/security/api/

**`tokens/bitstamp`**

**`tokens/bitstamp_secret`**

#### Binance

Change `import bitstamp as trading` to `import binance as trading` in `bot.py`.

Get API key and secret from https://www.binance.com/en/usercenter/settings/api-management

**`tokens/binance`**

**`tokens/binance_secret`**

#### Read alerts from Gmail

Update `gmail.py` constants to identify alerts.

Read header and use `oauth2.py` to get your token credentials.

**`tokens/gmail_at`** your email address

**`tokens/gmail`** token credentials

