#!/usr/bin/python3.6
# -*- coding: utf-8 -*-

import logging
import json
import gmail as alerts
import bitstamp as trading
from os import path
from telegram import Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import Unauthorized, TimedOut
from datetime import datetime, timedelta

with open("tokens/telegram", 'r') as telegram_token:
    TELEGRAM_API_TOKEN = telegram_token.read().strip()

with open("users", 'r') as users:
    ALLOWED_USERS = set(users.read().split('\n'))

NOT_ALLOWED = "You're not allowed to use this command."

def debug(update, answer):
    print(f"{update.message.from_user.username} ({update.message.chat_id}): {update.message.text}\n{answer}\n")

def is_allowed(update):
    return update.message.from_user.username in ALLOWED_USERS

def restricted(handler):
    def response(bot, update, **kwargs):
        if is_allowed(update):
            handler(bot, update, **kwargs)
        else:
            debug(update, NOT_ALLOWED)
            update.message.reply_text(NOT_ALLOWED)
    return response

def reply(update, text):
    debug(update, text)
    update.message.reply_text(text)

# BASIC AND DEFAULT HANDLERS

def start(bot, update):
    user = update.message.from_user
    text = f"Hi, {user.first_name}! I'm {NAME}, your trading assistant!\n\nAvailable commands:"
    text += "\n/start - Shows this message"
    text += "\n/ping - Test connection with trading API"
    text += "\n/price symbol - Current price for provided symbol"
    text += f"\n/account [{NAME}, {user.username}] - View your account or the bot account"
    if is_allowed(update):
        text += "\n/newAccount [balance] [currency] - Creates an account for trading"
        text += "\n/deleteAccount - Deletes your trading account"
        text += f"\n/history [{NAME}, {user.username}] - View your trades or the bot trades"
        text += "\n/trade [BUY, SELL] amount symbol [comment] - Order a trade for your account"
        text += "\n/tradeAll [BUY, SELL] symbol [comment] - Order a trade for your account with maximum available amount"
        text += f"\n/subscribe - Receive updates from the auto-trading of {NAME} account"
        text += f"\n/unsubscribe - Stop receiving updates from the auto-trading of {NAME} account"
    reply(update, text)

def unknown(bot, update):
    reply(update, f"Sorry, I didn't understand command {update.message.text}.")

def send(f, args=False):
    if args:
        def response(bot, update, args):
            reply(update, f(update.message.from_user.username, ' '.join(args)))
    else:
        def response(bot, update):
            reply(update, f(update.message.from_user.username))
    return response

def account(f):
    def response(bot, update, args):
        reply(update, f(NAME, update.message.from_user.username, ' '.join(args)))
    return response

# SUBSCRIPTIONS

SUBSCRIPTIONS = dict() # users to job

UPDATE_ALERTS_SECONDS = 1800

lastUpdate = datetime.now() - timedelta(days=1)
newAlert = False
lastAlert = None

def update_alerts():
    global lastAlert, newAlerts, lastUpdate
    now = datetime.now()
    if lastUpdate < now - timedelta(minutes=20):
        lastUpdate = now
        alerts.login()
        lastAlert = alerts.last_alert()
        alerts.logout()
        newAlert = lastAlert is not None

def subscription_update(bot, job):
    update_alerts()
    chat_id = job.context
    if newAlert:
        print("NEW ALERT. USER " + chat_id)
        if not trading.existsAccount(NAME):
            trading.newAccount(NAME)
        result = trading.tradeAll(NAME, lastAlert)
        text = f"🚨 {NAME} New Alert!\n\n{result}\n\nPerform /account {NAME} for more information"
        print(text)
        bot.send_message(chat_id=chat_id, text=text)

def loadSubscriptions():
    global updater
    if path.isfile('subscriptions'):
        with open('subscriptions', 'r') as subscriptionsFile:
            subscriptionUsers = json.load(subscriptionsFile)
            for subscriptor in subscriptionUsers:
                job = updater.job_queue.run_repeating(subscription_update, interval=UPDATE_ALERTS_SECONDS, first=30, context=subscriptor['chat_id'])
                SUBSCRIPTIONS[subscriptor['user']] = job

def saveSubscriptions():
    with open('subscriptions', 'w') as subscriptionsFile:
        json.dump([{ 'user': user, 'chat_id': job.context } for user, job in SUBSCRIPTIONS.items()], subscriptionsFile)

def subscribe(bot, update, args, job_queue):
    user = update.message.from_user.username
    if user not in SUBSCRIPTIONS:
        job = job_queue.run_repeating(subscription_update, interval=UPDATE_ALERTS_SECONDS, first=0, context=update.message.chat_id)
        SUBSCRIPTIONS[user] = job
        reply(update, f"Now you are subscribed to {NAME} trades.")
    else:
        reply(update, "Already subscribed.")

def __unsubscribe(update):
    user = update.message.from_user.username
    if user in SUBSCRIPTIONS:
        SUBSCRIPTIONS[user].schedule_removal()
        return "Unsubscribed successfully."
    else:
        return "You are not subscribed."

def unsubscribe(bot, update):
    reply(update, __unsubscribe(update))

# INITIALIZATION
bot = Bot(TELEGRAM_API_TOKEN)
NAME = bot.get_me().first_name
updater = Updater(TELEGRAM_API_TOKEN)
dispatcher = updater.dispatcher

# ERROR HANDLING
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def error_callback(bot, update, error):
    try:
        raise error
    except Unauthorized:
        __unsubscribe(update)
    except TimedOut:
        pass

dispatcher.add_error_handler(error_callback)

# TRADING HANDLERS
dispatcher.add_handler(CommandHandler('ping', send(trading.ping)))
dispatcher.add_handler(CommandHandler('price', send(trading.price, args=True), pass_args=True))
dispatcher.add_handler(CommandHandler('account', account(trading.account), pass_args=True))
dispatcher.add_handler(CommandHandler('history', restricted(account(trading.history)), pass_args=True))
dispatcher.add_handler(CommandHandler('trade', restricted(send(trading.trade, args=True)), pass_args=True))
dispatcher.add_handler(CommandHandler('tradeAll', restricted(send(trading.tradeAll, args=True)), pass_args=True))
dispatcher.add_handler(CommandHandler('newAccount', restricted(send(trading.newAccount, args=True)), pass_args=True))
dispatcher.add_handler(CommandHandler('deleteAccount', restricted(send(trading.deleteAccount))))
dispatcher.add_handler(CommandHandler('subscribe', restricted(subscribe), pass_args=True, pass_job_queue=True))
dispatcher.add_handler(CommandHandler('unsubscribe', restricted(unsubscribe)))

# DEFAULT HANDLERS
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.command, unknown))
dispatcher.add_handler(MessageHandler(Filters.text, start))

# START
trading.load()
loadSubscriptions()

updater.start_polling()

print(f"{NAME} Started!\n")

updater.idle()

# STOP
print("Saving accounts...")
trading.save()
saveSubscriptions()
print("Done! Goodbye!")