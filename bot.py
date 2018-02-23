#!/usr/bin/python3.6
# -*- coding: utf-8 -*-

import logging
import bitstamp as trading
from telegram import Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

with open("tokens/telegram", 'r') as telegram_token:
    TELEGRAM_API_TOKEN = telegram_token.read()

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
    text = f"Hi, {update.message.from_user.first_name}! I'm KiTrader, your trading assistant!\n\nAvailable commands:\n"
    text += "/start - Shows this message"
    if is_allowed(update):
        text += "\n/ping - Test connection with trading API\n"
        text += "/price symbol - Current price for provided symbol\n"
        text += f"/subscribe symbol - Subscribe for automatic trading of provided symbol\n"
        text += f"/unsubscribe - Unsubscribe from automatic trading"
    reply(update, text)

def unknown(bot, update):
    reply(update, f"Sorry, I didn't understand command {update.message.text}.")

def send(f, args=False):
    if args:
        def response(bot, update, args):
            reply(update, f(' '.join(args)))
    else:
        def response(bot, update):
            reply(update, f())
    return response

# SUBSCRIPTIONS

SUBSCRIPTIONS = dict() # users to job

def subscription_update(bot, job):
    user = job.context
    text = trading.subscription_update(user)
    if text:
        bot.send_message(chat_id=user, text=text)

def subscribe(bot, update, args, job_queue):
    user = update.message.chat_id
    (seconds, message) = trading.subscribe(user, ''.join(args))
    if seconds > 0:
        __unsubscribe(user)
        job = job_queue.run_repeating(subscription_update, interval=seconds, first=0, context=user)
        SUBSCRIPTIONS[user] = job
    reply(update, message)

def __unsubscribe(user):
    if user in SUBSCRIPTIONS:
        SUBSCRIPTIONS[user].schedule_removal()

def unsubscribe(bot, update):
    user = update.message.chat_id
    __unsubscribe(user)
    reply(update, trading.unsubscribe(user))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
# TODO (Error Handling): https://github.com/python-telegram-bot/python-telegram-bot/wiki/Exception-Handling

bot = Bot(TELEGRAM_API_TOKEN)
updater = Updater(TELEGRAM_API_TOKEN)
dispatcher = updater.dispatcher

# TRADING HANDLERS
dispatcher.add_handler(CommandHandler('ping', restricted(send(trading.ping))))
dispatcher.add_handler(CommandHandler('price', restricted(send(trading.price, args=True)), pass_args=True))
dispatcher.add_handler(CommandHandler('subscribe', restricted(subscribe), pass_args=True, pass_job_queue=True))
dispatcher.add_handler(CommandHandler('unsubscribe', restricted(unsubscribe)))

# DEFAULT HANDLERS
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.command, unknown))
dispatcher.add_handler(MessageHandler(Filters.text, start))

updater.start_polling()

print(f"{bot.get_me().username} Started!\n")

updater.idle()