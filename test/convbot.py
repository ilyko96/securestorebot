#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging

from telegram import ReplyKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
						  ConversationHandler)
from api_token import TOKEN

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					level=logging.INFO)

logger = logging.getLogger(__name__)

CHOOSING, TYPING_REPLY = range(2)

reply_keyboard = [['Topic 1', 'Topic 2']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

conv_handler = None

def facts_to_str(user_data):
	facts = list()

	for key, value in user_data.items():
		facts.append('{} - {}'.format(key, value))

	return "\n".join(facts).join(['\n', '\n'])

def alarm(alarm_ctx):
	global conv_handler
	job = alarm_ctx.job
	upd = job.context['upd']
	ctx = job.context['ctx']
	chat_id = upd.message.chat_id

	ctx.user_data.pop('job', None)

	logger.info('alarm')

	ctx.bot.send_message(chat_id,
		"It's alarm. Please choose:",
		reply_markup=markup)

	conv_handler.update_state(CHOOSING, conv_handler._get_key(upd))

def set_alarm(upd, ctx):
	if 'job' in ctx.user_data:
		ctx.user_data['job'].schedule_removal()
	ctx.user_data['job'] = ctx.job_queue.run_once(alarm, 7, context={'upd': upd, 'ctx': ctx})
	logger.info('set_alarm')

def start(update, context):
	update.message.reply_text(
		"Hi! Please choose topic.",
		reply_markup=markup)

	return CHOOSING


def regular_choice(update, context):
	text = update.message.text
	context.user_data['choice'] = text
	update.message.reply_text(
		'What about {}?'.format(text.lower()))

	return TYPING_REPLY


def received_information(update, context):
	user_data = context.user_data
	text = update.message.text
	category = user_data['choice']
	user_data[category] = text
	del user_data['choice']

	update.message.reply_text("Information:{}".format(facts_to_str(user_data)),
							  reply_markup=markup)

	return CHOOSING

def error(update, context):
	"""Log Errors caused by Updates."""
	logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
	global conv_handler
	# Create the Updater and pass it your bot's token.
	# Make sure to set use_context=True to use the new context based callbacks
	# Post version 12 this will no longer be necessary
	updater = Updater(TOKEN, use_context=True)

	# Get the dispatcher to register handlers
	dp = updater.dispatcher

	dp.add_handler(MessageHandler(Filters.regex('^alarm$'), set_alarm), group=0)

	# Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
	conv_handler = ConversationHandler(
		entry_points=[CommandHandler('start', start)],

		states={
			CHOOSING: [
				MessageHandler(Filters.regex('^(Topic 1|Topic 2)$'), regular_choice)
			],

			TYPING_REPLY: [
				MessageHandler(Filters.text,received_information)
			],
		},

		fallbacks=[

		]
	)

	dp.add_handler(conv_handler, group=1)

	# log all errors
	dp.add_error_handler(error)

	# Start the Bot
	updater.start_polling()

	# Run the bot until you press Ctrl-C or the process receives SIGINT,
	# SIGTERM or SIGABRT. This should be used most of the time, since
	# start_polling() is non-blocking and will stop the bot gracefully.
	updater.idle()


if __name__ == '__main__':
	main()