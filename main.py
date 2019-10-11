#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

"""
SecireStore
"""

import logging

from telegram import ReplyKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
						  ConversationHandler)

import db_handler as dbh
from api_token import TOKEN
from crypto import *

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					level=logging.INFO)

logger = logging.getLogger(__name__)

IDLE, ASK_PASSWORD, ACTION_PASSWORD, STORE, REVIEW = range(5)

BTN_PWD_STRONGER = 'Create stronger'
BTN_PWD_LEAVEWEAK = 'Leave weak'
BTN_PWD_TRYAGAIN = 'Try again'
BTN_PWD_STARTOVER = 'Start over'
BTN_ENCODE = 'Encode'
BTN_DECODE = 'Decode'
BTN_PWD_CHANGE = 'Change password'

reply_keyboard = [['Age', 'Favourite colour'],
				  ['Number of siblings', 'Something else...'],
				  ['Done']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


def facts_to_str(user_data):
	facts = list()

	for key, value in user_data.items():
		facts.append('{} - {}'.format(key, value))

	return "\n".join(facts).join(['\n', '\n'])

# Leave groups/channels and stay only in private chats
def check_leave_group(udp, ctx):
	if not udp.message.chat.type == udp.message.chat.PRIVATE:
		logger.warning("Added to group #{0}! Leaving...".format(udp.message.chat_id))
		udp.message.bot.leave_chat(udp.message.chat_id)

def start(update, context):
	chat_id = update.message.chat_id

	# Add new chat_id to DB
	chat = dbh.create_chat(chat_id)
	if chat > 1:
		logger.warning('Error while inserting new chat #{0} into DB: returned value {1}'.format(chat_id, chat))
	pwd = dbh.get_password(chat_id)
	if pwd is None:
		logger.warning('Error while retrieving password for chat #{0}.'.format(chat_id))
	if isinstance(pwd, str) and len(pwd) > 0:
		update.message.reply_text(
			"Hi again! My name is Charles. You can trust me all your secrets and nobody will ever have known about them except you.\n"
			"Use menu buttons to start securely storing your data.")
		return IDLE

	update.message.reply_text(
		"Hi! My name is Charles. You can trust me all your secrets and nobody will ever have known about them except you. "
		"Please send me the password to start.\n\n"
		"Notice, there is no way recover data if the password is lost! So, please, remember it carefully!!!")
	return ASK_PASSWORD

def check_password(upd, ctx):
	is_weak = is_password_weak(upd.message.text)
	hash = get_hash(upd.message.text)
	upd.message.delete()
	# First entry of password
	if 'password' not in ctx.user_data:
		ctx.user_data['password'] = hash
		if is_weak:
			upd.message.reply_text('The password you entered is weak and does not provide enough security!\n'
								   'It is highly recommended to come up with reliable password, which satisfies:\n'
								   '- At least 8 symbols\n'
								   '- Consist of a-z, A-Z, 0-9 and/or special symbols @#$%^&+=\n\n'
								   'Do you want to change your opinion and create stronger password?',
								   reply_markup=ReplyKeyboardMarkup([[BTN_PWD_STRONGER, BTN_PWD_LEAVEWEAK]], one_time_keyboard=True))
			return ACTION_PASSWORD
		else:
			upd.message.reply_text('Please send me the password again (and remember it properly!).')
			return ASK_PASSWORD
	# Repetition of password
	else:
		if ctx.user_data['password'] != hash:
			upd.message.reply_text('Ooopsie! The passwords do not match! Please try again or create new password.',
								   reply_markup=ReplyKeyboardMarkup([[BTN_PWD_TRYAGAIN, BTN_PWD_STARTOVER]], one_time_keyboard=True))
			return ACTION_PASSWORD
		else:
			dbh.set_password(upd.message.chat_id, ctx.user_data['password'])
			upd.message.reply_text('Password successfully created! You can now begin securely storing your data',
								   reply_keyboard=ReplyKeyboardMarkup([[BTN_ENCODE, BTN_DECODE],
																	   [BTN_PWD_CHANGE]], one_time_keyboard=True))
			return IDLE

def weak_password(upd, ctx):
	text = upd.message.text
	if text == BTN_PWD_STRONGER:
		ctx.user_data.pop('password', None)
		upd.message.reply_text('Very nice decision! Please send me strong password now.\n'
							   'Notice, there is no way recover data if the password is lost! So, please, remember it carefully!!!')
		return ASK_PASSWORD
	elif text == BTN_PWD_LEAVEWEAK:
		upd.message.reply_text('I\'m only offering and it is your responsibility for this decision.\n'
							   'Please repeat the password again, so I can check that you remembered it properly')
		return ASK_PASSWORD
	elif text == BTN_PWD_TRYAGAIN:
		upd.message.reply_text('Please send me the password again (and remember it properly!).')
		return ASK_PASSWORD
	elif text == BTN_PWD_STARTOVER:
		ctx.user_data.pop('password', None)
		upd.message.reply_text('That\'s a good idea. Create a new strong password, remember it and send it to me.')
		return ASK_PASSWORD
	pass

def regular_choice(update, context):
	text = update.message.text
	context.user_data['choice'] = text
	update.message.reply_text(
		'Your {}? Yes, I would love to hear about that!'.format(text.lower()))

	return TYPING_REPLY


def custom_choice(update, context):
	update.message.reply_text('Alright, please send me the category first, '
							  'for example "Most impressive skill"')

	return TYPING_CHOICE


def received_information(update, context):
	user_data = context.user_data
	text = update.message.text
	category = user_data['choice']
	user_data[category] = text
	del user_data['choice']

	update.message.reply_text("Neat! Just so you know, this is what you already told me:"
							  "{} You can tell me more, or change your opinion"
							  " on something.".format(facts_to_str(user_data)),
							  reply_markup=markup)

	return CHOOSING


def done(update, context):
	user_data = context.user_data
	if 'choice' in user_data:
		del user_data['choice']

	update.message.reply_text("I learned these facts about you:"
							  "{}"
							  "Until next time!".format(facts_to_str(user_data)))

	user_data.clear()
	return ConversationHandler.END


def error(update, context):
	"""Log Errors caused by Updates."""
	logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
	# Create the Updater and pass it your bot's token.
	# Make sure to set use_context=True to use the new context based callbacks
	# Post version 12 this will no longer be necessary
	updater = Updater(TOKEN, use_context=True)

	# Get the dispatcher to register handlers
	dp = updater.dispatcher

	dp.add_handler(MessageHandler(Filters.all, check_leave_group), group=0)

	# Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
	conv_handler = ConversationHandler(
		entry_points=[CommandHandler('start', start)],

		states={
			IDLE: [MessageHandler(Filters.regex('^(Age|Favourite colour|Number of siblings)$'),
								  regular_choice),
				   MessageHandler(Filters.regex('^Something else...$'),
								  custom_choice)
				   ],

			ASK_PASSWORD: [MessageHandler(Filters.text, check_password)],

			ACTION_PASSWORD: [MessageHandler(Filters.text, weak_password)],
		},

		fallbacks=[MessageHandler(Filters.regex('^Done$'), done)]
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