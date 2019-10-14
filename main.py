#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

"""
SecureStore
"""
import logging

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
						  ConversationHandler)

import db_handler as dbh
from api_token import TOKEN
from crypto import *
from util import *
from constants import *

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


conv_handler = None
markup_idle = [[BTN_RECORD, BTN_BROWSE], [BTN_SETTINGS, BTN_LOGOUT]]

def store_msg_id(ctx, msg):
	ctx.chat_data['msg_ids'].append(msg.message_id)

# Checks and actions needed to be performed on each atomic signal received from user
def every_signal_checks(upd, ctx):
	# Leave all groups/channels and stay only in private chats
	if not upd.message.chat.type == upd.message.chat.PRIVATE:
		logger.warning("Added to group #{0}! Leaving...".format(upd.message.chat_id))
		upd.message.bot.leave_chat(upd.message.chat_id)

	# Check authorization state and update authorization timer
	elif is_authorized(ctx):
		update_authorization_timer(upd, ctx)

	# Collect all message-ids in context in order to remove everything on logout
	store_msg_id(ctx, upd.message)

# Checks if authorization expired and returns True - is still authorized, False - o\w
def is_authorized(ctx):
	return 'authorized' in ctx.chat_data \
			and ctx.chat_data['authorized'] is not None \
			and timestamp_now() - ctx.chat_data['authorized'] <= DEFAULT_UNAUTH_TIMER

# Is called when user is inactive for specified time. Shows corresponding msg and TODO: changes conversation state
def authorization_alarm(alarm_ctx):
	global conv_handler
	job = alarm_ctx.job
	upd = job.context['upd']
	ctx = job.context['ctx']
	chat_id = upd.message.chat_id

	if DEFAULT_CLEAR_ON_ALARM:
		clear_history(upd, ctx)
	msg = ctx.bot.send_message(chat_id, text='You were inactive for {0} seconds, so now you need to prove your identity.\n'
									   'Enter the password, please.'.format(DEFAULT_UNAUTH_TIMER), reply_markup=ReplyKeyboardRemove())
	store_msg_id(ctx, msg)
	ctx.chat_data.pop('authorized_job', None)
	update_authorization_timer(upd, ctx, unauthorize=True)
	ctx.chat_data['password_mode'] = MODE_PWD_TEST
	logger.info('authorization_alarm')

	conv_handler.update_state(STATE_TYPING_PASSWORD, conv_handler._get_key(upd))

# Called each time, when user makes action. Sets up new alarm instead of prev and updates authorization timestamp
def update_authorization_timer(upd, ctx, unauthorize=False):
	ctx.chat_data['authorized'] = None if unauthorize else timestamp_now()
	logger.info('update_authorization_timer: authorized={0}   unauthorize={1}'.format(ctx.chat_data['authorized'], unauthorize))
	if unauthorize:
		for job in ctx.job_queue.jobs():
			job.schedule_removal()
		logger.info('update_authorization_timer: all jobs removed'.format(ctx.chat_data['authorized'], unauthorize))
	else:
		if 'authorized_job' in ctx.chat_data:
			logger.info('update_authorization_timer: job removed'.format(ctx.chat_data['authorized'], unauthorize))
			ctx.chat_data['authorized_job'].schedule_removal()
		ctx.chat_data['authorized_job'] = ctx.job_queue.run_once(authorization_alarm, DEFAULT_UNAUTH_TIMER, context={'upd': upd, 'ctx': ctx})
		logger.info('update_authorization_timer: job created'.format(ctx.chat_data['authorized'], unauthorize))

# Entry point
def start(upd, ctx):
	# ctx.chat_data contains 4 password fields:
	#	'start_password'- True if password was given instead of /start command
	# 	'password'		- contains hash-sum of real password
	#	'password_mode'	- takes one of MODE_PWD_SET/MODE_PWD_TEST/MODE_PWD_AUTHORIZED and indicates current state
	#	'authorized'	- either None/integer, correspondingly indicating absence of authorization or the time of last authorization

	chat_id = upd.message.chat_id

	dbh.create_chat_if_not_exist(chat_id) # Add new chat_id to DB
	pwd = dbh.get_password(chat_id)

	ctx.chat_data['msg_ids'] = []

	# if pwd is None: # Seems to be redundant
	# 	logger.warning('Chat #{0} could not be found. Creating new entry.'.format(chat_id))

	# If password is already set
	if pwd is not None and len(pwd) > 0:
		if isinstance(pwd, str):
			pwd = pwd.encode()
		ctx.chat_data['password'] = pwd

		# Handle case when start() is called from received_password() due to pwd given instead of /start
		if 'start_password' in ctx.chat_data and ctx.chat_data['start_password'] is not None:
			ctx.chat_data.pop('start_password', None)
			ctx.chat_data['password_mode'] = MODE_PWD_TEST
			update_authorization_timer(upd, ctx, unauthorize=True)
			return

		# If authorization still valid
		if is_authorized(ctx):
			ctx.chat_data['password_mode'] = MODE_PWD_AUTHORIZED
			msg = upd.message.reply_text(
				"Hi again! My name is Charles. You can trust me all your secrets and nobody will ever have known about them except you.\n"
				"Use menu buttons to start securely storing your data.",
				reply_markup=ReplyKeyboardMarkup([[BTN_RECORD, BTN_BROWSE],
												  [BTN_PWD_CHANGE]], one_time_keyboard=True))
			store_msg_id(ctx, msg)
			return STATE_IDLE
		# If no authorization or expired
		else:
			ctx.chat_data['password_mode'] = MODE_PWD_TEST
			update_authorization_timer(upd, ctx, unauthorize=True)
			msg = upd.message.reply_text(
				"Hi again! My name is Charles. You can trust me all your secrets and nobody will ever have known about them except you.\n"
				"Please, send me the password first, so I can trust you")
			store_msg_id(ctx, msg)
			return STATE_TYPING_PASSWORD

	# If password need to be set
	ctx.chat_data['password_mode'] = MODE_PWD_SET
	update_authorization_timer(upd, ctx, unauthorize=True)
	msg = upd.message.reply_text(
		"Hi! My name is Charles. You can trust me all your secrets and nobody will ever have known about them except you. "
		"Please send me the password to start.\n\n"
		"Notice, there is no way recover data if the password is lost! So, please, remember it for sure!!!")
	store_msg_id(ctx, msg)
	return STATE_TYPING_PASSWORD

# Checks given password
def received_password(upd, ctx):
	# this is triggered for every signal, filter here only those, which have text
	if upd.message.text is None or len(upd.message.text) == 0:
		return

	chat_id = upd.message.chat_id

	is_weak = is_password_weak(upd.message.text)
	hash = get_hash(upd.message.text)
	upd.message.delete()

	# Case when entry point is not /start but password
	if 'password_mode' not in ctx.chat_data:
		# logger.warning('Not \'password_mode\' key in \'ctx.chat_data\' dict! Considering \'password_set\' action')
		ctx.chat_data['start_password'] = True
		start(upd, ctx)

	# Nothing to do if already authorized
	if ctx.chat_data['password_mode'] == MODE_PWD_AUTHORIZED:
		msg = upd.message.reply_text('Authorized successfully! Use menu buttons to securely store your secrets',
							   reply_markup=ReplyKeyboardMarkup(markup_idle, one_time_keyboard=True))
		store_msg_id(ctx, msg)
		return STATE_IDLE

	# Entered password needs to be used for authorization
	if ctx.chat_data['password_mode'] == MODE_PWD_TEST:
		# Entered password is correct
		if ctx.chat_data['password'] == hash:
			ctx.chat_data['password_mode'] = MODE_PWD_AUTHORIZED
			update_authorization_timer(upd, ctx)
			msg = upd.message.reply_text('Successfully authorized! You can now begin securely storing your data',
								   reply_markup=ReplyKeyboardMarkup(markup_idle, one_time_keyboard=True))
			store_msg_id(ctx, msg)
			return STATE_IDLE
		# Entered password is incorrect
		else:
			# TODO: add here counter and only show keyboard on 3rd attempt
			update_authorization_timer(upd, ctx, unauthorize=True)
			msg = upd.message.reply_text('Ooopsie... Entered password is incorrect! You can try again or set up a new password.\n',
								   reply_markup=ReplyKeyboardMarkup([[BTN_PWD_TRYAGAIN, BTN_PWD_NEW]], one_time_keyboard=True))
			store_msg_id(ctx, msg)
			return STATE_CHOOSE_PASSWORD_ACTION

	# User needs to set up the password
	if ctx.chat_data['password_mode'] == MODE_PWD_SET:
		# First entry of password
		if 'password' not in ctx.chat_data:
			ctx.chat_data['password'] = hash
			if is_weak:
				msg = upd.message.reply_text('The password you entered is weak and does not provide enough security!\n'
									   'It is highly recommended to come up with reliable password, which satisfies:\n'
									   '- At least 8 symbols\n'
									   '- Consist of a-z, A-Z, 0-9 and/or special symbols @#$%^&+=\n\n'
									   'Do you want to change your opinion and create stronger password?',
									   reply_markup=ReplyKeyboardMarkup([[BTN_PWD_STRONGER, BTN_PWD_LEAVEWEAK]], one_time_keyboard=True))
				store_msg_id(ctx, msg)
				return STATE_CHOOSE_PASSWORD_ACTION
			else:
				msg = upd.message.reply_text('Please send me the password again (and remember it properly!).')
				store_msg_id(ctx, msg)
				return STATE_TYPING_PASSWORD
		# Repetition of password
		else:
			if ctx.chat_data['password'] != hash:
				msg = upd.message.reply_text('Ooopsie! The passwords do not match! Please try again or create new password.',
									   reply_markup=ReplyKeyboardMarkup([[BTN_PWD_TRYAGAIN, BTN_PWD_STARTOVER]], one_time_keyboard=True))
				store_msg_id(ctx, msg)
				return STATE_CHOOSE_PASSWORD_ACTION
			else:
				dbh.set_password(upd.message.chat_id, ctx.chat_data['password'])
				ctx.chat_data['password_mode'] = MODE_PWD_AUTHORIZED
				update_authorization_timer(upd, ctx)
				msg = upd.message.reply_text('Password successfully created! You can now begin securely storing your data',
									   reply_markup=ReplyKeyboardMarkup(markup_idle, one_time_keyboard=True))
				store_msg_id(ctx, msg)
				return STATE_IDLE

# TODO: change elifs to handlers (or just somehow reorganize properly)
# Handles user input password
def password_btn_clicked(upd, ctx):
	text = upd.message.text
	chat_id = upd.message.chat_id

	if text == BTN_PWD_STRONGER:
		ctx.chat_data.pop('password', None)
		msg = upd.message.reply_text('Very nice decision! Please send me strong password now.\n'
							   'Notice, there is no way recover data if the password is lost! So, please, remember it carefully!!!')
		store_msg_id(ctx, msg)
		return STATE_TYPING_PASSWORD
	elif text == BTN_PWD_LEAVEWEAK:
		msg = upd.message.reply_text('I\'m only offering and it is your responsibility for this decision.\n'
							   'Please repeat the password again, so I can check that you remembered it properly')
		store_msg_id(ctx, msg)
		return STATE_TYPING_PASSWORD
	elif text == BTN_PWD_TRYAGAIN:
		msg = upd.message.reply_text('Send me the password again (and remember it properly!).\n'
							   'Please check if [CAPS Lock] is off and you are using correct keyboard layout.')
		store_msg_id(ctx, msg)
		return STATE_TYPING_PASSWORD
	elif text == BTN_PWD_STARTOVER:
		ctx.chat_data.pop('password', None)
		msg = upd.message.reply_text('That\'s a good idea. Create a new strong password, remember it and send it to me.')
		store_msg_id(ctx, msg)
		return STATE_TYPING_PASSWORD
	elif text == BTN_PWD_NEW:
		records = dbh.get_records_overview(chat_id)
		ctx.chat_data['number_of_records'] = len(records)
		msg = upd.message.reply_text('This will completely destroy all stored information '
							   '(incl. current password fingerprint and all records) '
							   'and start over from scratch.\n'
							   'If you really want to continue send me the following message: \'{0}\''
							   .format(CONSCIOUS_CONFIRMATION_MSG.format(len(records))))
		store_msg_id(ctx, msg)
		return STATE_CHOOSE_PASSWORD_ACTION
	else:
		if 'number_of_records' not in ctx.chat_data or ctx.chat_data['number_of_records'] is None:
			records = dbh.get_records_overview(chat_id)
			ctx.chat_data['number_of_records'] = len(records)
		if text == CONSCIOUS_CONFIRMATION_MSG.format(ctx.chat_data['number_of_records']):
			ndel_chat, ndel_recs = dbh.delete_all(chat_id)
			ctx.chat_data.clear()
			msg = upd.message.reply_text('Your data was successfully destroyed! Our database now is by {0} records thinner ;)\n'
								   'Have a nice day and feel free to come back any time you want.\n'
								   'Use command /start (or the button below) to start over.'.format(ndel_recs),
								   reply_markup=ReplyKeyboardMarkup([[BTN_START]], one_time_keyboard=True))
			store_msg_id(ctx, msg)
			return STATE_START

# Delete all messages by their ids stored in chat_data['msg_ids'] for current session
def clear_history(upd, ctx):
	for msg_id in ctx.chat_data['msg_ids']:
		try: ctx.bot.delete_message(upd.message.chat_id, msg_id)
		except: pass

# Logs user out, making him unauthorized
def logout(upd, ctx):
	if DEFAULT_CLEAR_ON_LOGOUT:
		clear_history(upd, ctx)
	msg = ctx.bot.send_message(upd.message.chat_id,
						 text='You were successfully logged out!\n'
							  'Just send me your password whenever you want log in back again.', reply_markup=ReplyKeyboardRemove())
	store_msg_id(ctx, msg)
	update_authorization_timer(upd, ctx, unauthorize=True)
	ctx.chat_data['password_mode'] = MODE_PWD_TEST
	return STATE_TYPING_PASSWORD

# Requests user to enter data
# TODO: only supports text messages now. Extend!
def idle_button_clicked(upd, ctx):
	if upd.message.text == BTN_RECORD:
		msg = upd.message.reply_text(
			"Tell me your secret")
		store_msg_id(ctx, msg)
		return STATE_TYPING_RECORD

# TODO: handle case when 1 msg is not enough to deliver all data
# Receives message, encrypts and stores into DB
def encrypt_data(upd, ctx):
	key = dbh.get_password(upd.message.chat_id)
	ln = len(upd.message.text)
	encrypted = encrypt_string(upd.message.text, key)
	upd.effective_message.delete()

	ctx.chat_data['data'] = encrypted

	msg = upd.message.reply_text(
		"Your message of length {0} has been successfully encrypted. Do you want to store it?".format(ln),
		reply_markup=ReplyKeyboardMarkup([[BTN_RECORD_SAVE, BTN_RECORD_CANCEL]], one_time_keyboard=True))
	store_msg_id(ctx, msg)
	return STATE_CONFIRMING_RECORD

# Handles user confirmation for storing created record
def confirm_adding_record(upd, ctx):
	# Should never be true due to code consistency
	if 'data' not in ctx.chat_data or ctx.chat_data['data'] is None:
		logger.warning('No data found in context for \'chat_id\'={}! Continuing without storing data!'.format(upd.message.chat_id))
		msg = upd.message.reply_text(
			"Error occured while saving your data. This case is already reported. Please try again later",
			reply_markup=ReplyKeyboardMarkup(markup_idle, one_time_keyboard=True))
		store_msg_id(ctx, msg)

	rec = dbh.create_record(upd.message.chat_id, ctx.chat_data['data'])

	if rec != 1:
		logger.warning(
			'Could not save record to database. chat_id=\'{0}\', data=\'{1}\''.format(upd.message.chat_id, ctx.chat_data['data']))
		msg = upd.message.reply_text(
			"Error occured while saving your data. This case is already reported. Please try again later",
			reply_markup=ReplyKeyboardMarkup(markup_idle, one_time_keyboard=True))
		store_msg_id(ctx, msg)
		return STATE_IDLE

	ln = len(ctx.chat_data['data'])
	ctx.chat_data.pop('data', None)
	msg = upd.message.reply_text(
		"Your message of length {0} has been successfully saved".format(ln),
		reply_markup=ReplyKeyboardMarkup(markup_idle, one_time_keyboard=True))
	store_msg_id(ctx, msg)
	return STATE_IDLE

# Handles user cancellation for storing created record
def cancel_adding_record(upd, ctx):
	ln = len(ctx.chat_data['data'])
	ctx.chat_data.pop('data', None)
	msg = upd.message.reply_text(
		"Your message of length {0} has been successfully deleted.".format(ln),
		reply_markup=ReplyKeyboardMarkup(markup_idle, one_time_keyboard=True))
	store_msg_id(ctx, msg)
	return STATE_IDLE

# Handles click on button 'Browse' from STATE_IDLE
def browse_records(upd, ctx):
	chat_id = upd.message.chat_id

	records = dbh.get_records_overview(chat_id)

	# Should probably never happen ;)
	if records == None:
		msg = upd.message.reply_text(
			"Some error happend while trying to retrieve your data. This case has already been reported. Try again later",
			reply_markup=ReplyKeyboardMarkup(markup_idle, one_time_keyboard=True))
		store_msg_id(ctx, msg)
		return STATE_IDLE
	# If no data found in DB
	elif len(records) == 0:
		msg = upd.message.reply_text(
			"You don't have any records yet. Use menu buttons to add new.",
			reply_markup=ReplyKeyboardMarkup(markup_idle, one_time_keyboard=True))
		store_msg_id(ctx, msg)
		return STATE_IDLE
	# If data has been found

	ctx.chat_data['data_overview'] = records
	msg_list = ''
	i = 0
	for r in records:
		if i >= BROWSE_PAGE_LIMIT:
			break
		msg_list += '\n{0} [{1}]'.format(records[i]['timestamp'], records[i]['size'])
		i += 1

	msg = upd.message.reply_text(
		"Last {0}/{1} records are:\n{2}".format(len(records), BROWSE_PAGE_LIMIT, msg_list),
		reply_markup=ReplyKeyboardMarkup(markup_idle, one_time_keyboard=True))
	store_msg_id(ctx, msg)
	return STATE_IDLE

def error(update, context):
	"""Log Errors caused by Updates."""
	logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
	global conv_handler

	updater = Updater(TOKEN, use_context=True)
	dp = updater.dispatcher

	# Handler for every signal checks: leave groups and check authorization
	dp.add_handler(MessageHandler(Filters.all, every_signal_checks), group=0)
	# Main conversation handler
	conv_handler = ConversationHandler(
		# Entry point
		entry_points=[
			CommandHandler('start', start),
			MessageHandler(Filters.all, received_password)
		],

		states={
			STATE_START: [
				CommandHandler('start', start),
				MessageHandler(Filters.regex('^{}$'.format(BTN_START)), start)
			],
			STATE_TYPING_PASSWORD: [
				MessageHandler(Filters.all, received_password)
			],
			STATE_CHOOSE_PASSWORD_ACTION: [
				MessageHandler(Filters.text, password_btn_clicked)
			],
			STATE_IDLE: [
				MessageHandler(Filters.regex('^{0}$'.format(BTN_RECORD)), idle_button_clicked),
				MessageHandler(Filters.regex('^{0}$'.format(BTN_LOGOUT)), logout),
				MessageHandler(Filters.regex('^{0}$'.format(BTN_BROWSE)), browse_records)
			],
			STATE_TYPING_RECORD: [
				MessageHandler(Filters.text, encrypt_data)
			],
			STATE_CONFIRMING_RECORD: [
				MessageHandler(Filters.regex('^{0}$'.format(BTN_RECORD_SAVE)), confirm_adding_record),
				MessageHandler(Filters.regex('^{0}$'.format(BTN_RECORD_CANCEL)), cancel_adding_record)
			]
		},

		fallbacks=[
			# MessageHandler(Filters.regex('^Done$'), done)
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