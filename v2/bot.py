import logging

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler)

import v2.db_manager as dbm
from api_token import TOKEN
from v2.handlers import *
from crypto import *
from util import *
from v2.constants import *

def main():
	global conv_handler

	updater = Updater(TOKEN, use_context=True)
	dp = updater.dispatcher

	# Main conversation handler
	conv_handler = ConversationHandler(
		# Entry point
		entry_points=[
			CommandHandler('start', cmd_start),
			MessageHandler(Filters.all, password_auth_received)
		],

		states={
			STATE_UNAUTH: [
				CommandHandler('start', cmd_start),
				MessageHandler(Filters.all, password_auth_received)
			],
			STATE_IDLE: [
				MessageHandler(Filters.all, debug_repeat)
			],
			STATE_PASSWORD_SETUP: [
				MessageHandler(Filters.all, password_set_received)
			]
		},

		fallbacks=[
			# MessageHandler(Filters.regex('^Done$'), done)
		]
	)

	dp.add_handler(MessageHandler(Filters.all, msg_leave_groups), group=0)
	dp.add_handler(MessageHandler(Filters.all, msg_update_auth), group=1)
	dp.add_handler(conv_handler, group=2)

	dp.add_error_handler(hndl_error)

	# Start the Bot
	updater.start_polling()

	# Run the bot until you press Ctrl-C or the process receives SIGINT,
	# SIGTERM or SIGABRT. This should be used most of the time, since
	# start_polling() is non-blocking and will stop the bot gracefully.
	updater.idle()


if __name__ == '__main__':
	main()