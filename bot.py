#!/usr/bin/python3.6
# -*- coding: utf-8 -*-

import pytz
import logging
import json
import gmail as alerts
import bitstamp as trading

from os import path
from telegram import Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import Unauthorized, TimedOut
from datetime import datetime, timedelta

try:
    with open("tokens/telegram", 'r') as telegram_token:
        TELEGRAM_API_TOKEN = telegram_token.read().strip()
except FileNotFoundError:
    print("tokens/telegram not found!")
    exit(1)

try:
    with open("superusers", 'r') as users:
        SUPERUSERS = set(users.read().split('\n'))
except FileNotFoundError:
    SUPERUSERS = set()

def debug(update, answer):
    print(f"{datetime.now()} - {update.message.from_user.username} ({update.message.chat_id}): {update.message.text}\n{answer}\n")

def reply(update, text):
    debug(update, text)
    update.message.reply_text(text)

def is_superuser(update):
    return update.message.from_user.username in SUPERUSERS

def restricted(handler):
    def response(update, context, **kwargs):
        if is_superuser(update):
            handler(update, context, **kwargs)
        else:
            reply(update, "You're not allowed to use this command.")
    return response

# BASIC AND DEFAULT HANDLERS

def start(update, context):
    user = update.message.from_user
    superuser = is_superuser(update)
    text = f"Hi, {user.first_name}! I'm {NAME}, your trading assistant!\n\nAvailable commands:"
    # Basic commands
    text += "\n/start - Shows this message"
    text += "\n/ping - Test connection with trading API"
    text += "\n/list - Show the available symbols"
    text += "\n/price symbol - Current price for provided symbol"
    # Account commands
    text += "\n/newAccount [balance] [currency] - Creates an account for mock trading (free)"
    text += "\n\te.g. /newAccount 1000 USD"
    text += "\n/deleteAccount - Deletes your trading account"
    if superuser:
        text += f"\n/account [{NAME}, {user.username}] - View your account or the bot account"
        text += f"\n/history [{NAME}, {user.username}] - View your trades or the bot trades"
    else:
        text += f"\n/account - View your account"
        text += f"\n/history - View your trades"
    text += "\n/trade [BUY, SELL] amount symbol [comment] - Order a trade for your account"
    text += "\n\te.g. /trade BUY 0.1 ETH"
    text += "\n/tradeAll [BUY, SELL] symbol [comment] - Order a trade for your account with maximum available amount"
    text += "\n\te.g. /tradeAll BUY BTC"
    text += f"\nTrading Fee: {trading.FEE * 100}%"
    # Auto-trading commands
    if superuser:
        text += f"\n/subscribe - Receive updates from the {NAME} auto-trading account"
        text += f"\n/unsubscribe - Stop receiving updates from the {NAME} auto-trading account"
        text += f"\n/update - Forces an update of the {NAME} auto-trading subscription"
    reply(update, text)

def unknown(update, context):
    reply(update, f"Sorry, I didn't understand command {update.message.text}.")

def wrap(f):
    def response(update, context):
        reply(update, f())
    return response

def send(f, args=False):
    if args:
        def response(update, context):
            reply(update, f(update.message.from_user.username, ' '.join(context.args)))
    else:
        def response(update, context):
            reply(update, f(update.message.from_user.username))
    return response

def account(f):
    def response(update, context):
        reply(update, f(NAME, update.message.from_user.username, is_superuser(update), ' '.join(context.args)))
    return response

# SUBSCRIPTIONS

SUBSCRIPTIONS = dict() # users to job

UPDATE_ALERTS_SECONDS = 900

lastUpdate = alerts.get_last_alert_date() or datetime.now(pytz.UTC) - timedelta(hours=24)
newAlerts = []
updating = False

def update_alerts(force=False):
    global lastUpdate, newAlerts, updating
    if updating or not alerts.ENABLED:
        return
    updating = True
    now = datetime.now(pytz.UTC)
    if force or lastUpdate < now - timedelta(seconds=UPDATE_ALERTS_SECONDS // 2):
        lastUpdate = now
        alerts.login()
        newAlerts = alerts.update_alerts()
        alerts.logout()
    else:
        newAlerts = []
    updating = False

def subscription_update(bot, chat_id, force=False):
    update_alerts(force)
    for _, newAlertText in newAlerts:
        if not trading.existsAccount(NAME):
            trading.newAccount(NAME)
        result = trading.tradeAll(NAME, newAlertText)
        if 'BUY' not in result and 'SELL' not in result:
            result = newAlertText + '\n' + result
        text = f"🚨 New Alert!\n\n{result}\n\nPerform /account {NAME} for more information."
        print(text)
        bot.send_message(chat_id=chat_id, text=text)

def subscription_job(context):
    subscription_update(context.bot, chat_id=context.job.context)

def force_update(update, context):
    if not alerts.ENABLED:
        reply(update, "Alerts are disabled.")
        return
    reply(update, "Updating. Please, wait a few seconds.")
    subscription_update(context.bot, update.message.chat_id, force=True)
    if not newAlerts:
        reply(update, "Alerts are up to date.")

def loadSubscriptions():
    global updater
    if path.isfile('subscriptions'):
        with open('subscriptions', 'r') as subscriptionsFile:
            subscriptionUsers = json.load(subscriptionsFile)
            for subscriber in subscriptionUsers:
                job = updater.job_queue.run_repeating(subscription_job, interval=UPDATE_ALERTS_SECONDS, first=30, context=subscriber['chat_id'])
                SUBSCRIPTIONS[subscriber['user']] = job

def saveSubscriptions():
    with open('subscriptions', 'w') as subscriptionsFile:
        json.dump([{ 'user': user, 'chat_id': job.context } for user, job in SUBSCRIPTIONS.items()], subscriptionsFile)

def subscribe(update, context):
    user = update.message.from_user.username
    if user not in SUBSCRIPTIONS:
        job = context.job_queue.run_repeating(subscription_job, interval=UPDATE_ALERTS_SECONDS, first=0, context=update.message.chat_id)
        SUBSCRIPTIONS[user] = job
        reply(update, f"Now you are subscribed to {NAME} trades.")
    else:
        reply(update, "Already subscribed.")

def __unsubscribe(update):
    user = update.message.from_user.username
    if user in SUBSCRIPTIONS:
        SUBSCRIPTIONS[user].schedule_removal()
        SUBSCRIPTIONS.pop(user)
        return "Unsubscribed successfully."
    else:
        return "You are not subscribed."

def unsubscribe(update, context):
    reply(update, __unsubscribe(update))

# INITIALIZATION
print("Starting bot...")

bot = Bot(TELEGRAM_API_TOKEN)
NAME = bot.get_me().first_name
updater = Updater(TELEGRAM_API_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# ERROR HANDLING
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARN)

def error_callback(update, context):
    try:
        raise context.error
    except Unauthorized:
        __unsubscribe(update)
    except TimedOut:
        pass

print('Adding command handlers...')

dispatcher.add_error_handler(error_callback)

# TRADING HANDLERS
dispatcher.add_handler(CommandHandler('ping', wrap(trading.ping)))
dispatcher.add_handler(CommandHandler('price', send(trading.price, args=True)))
dispatcher.add_handler(CommandHandler('list', send(trading.list_symbols)))
dispatcher.add_handler(CommandHandler('account', account(trading.account)))
dispatcher.add_handler(CommandHandler('history', account(trading.history)))
dispatcher.add_handler(CommandHandler('trade', send(trading.trade, args=True)))
dispatcher.add_handler(CommandHandler('tradeAll', send(trading.tradeAll, args=True)))
dispatcher.add_handler(CommandHandler('newAccount', send(trading.newAccount, args=True)))
dispatcher.add_handler(CommandHandler('deleteAccount', send(trading.deleteAccount)))
dispatcher.add_handler(CommandHandler('subscribe', restricted(subscribe), pass_job_queue=True))
dispatcher.add_handler(CommandHandler('unsubscribe', restricted(unsubscribe)))
dispatcher.add_handler(CommandHandler('update', restricted(force_update)))

# TODO: Command /selectApi [Bitstamp | Binance]

# DEFAULT HANDLERS
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.command, unknown))
dispatcher.add_handler(MessageHandler(Filters.text, start))

# START
print('Loading trading API...')
trading.load()

print('Loading subscriptions...')
loadSubscriptions()

updater.start_polling()

print(f"\n{NAME} Started!\n")

updater.idle()

# STOP
print("Saving accounts...")
trading.save()
saveSubscriptions()

print("Done! Goodbye!")
