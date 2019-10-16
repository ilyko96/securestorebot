import logging
from v2.constants import *
from v2.db_manager import *
from util import *

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

###########################################
############ Handlers section #############
###########################################

# Error handler
def hndl_error(upd, ctx):
	logger.warning('Update "%s" caused error "%s"', upd, ctx.error)

# Command handler for /reset
def cmd_reset(upd, ctx):
	pass

# Message handler for all messages. Leaves groups and channels and stays only in private chats.
def msg_leave_groups(upd, ctx):
	if not upd.message.chat.type == upd.message.chat.PRIVATE:
		logger.warning("Added to group #{0}! Leaving...".format(upd.message.chat_id))
		upd.message.bot.leave_chat(upd.message.chat_id)

# Message handler for all messages. Updates timestamp of last action and resets unauth alarms.
def msg_update_auth(upd, ctx):
	pass

# Command handler for /start
def cmd_start(upd, ctx):
	chat_id = upd.message.chat_id

	# If already authorized then just switch to IDLE
	if is_authorized(ctx):
		upd.message.reply_text('You are already authorized')
		return STATE_IDLE

	# If you are here, then chat is not authorized.
	# If chat exists in DB
	if chat_exist(chat_id):
		upd.message.reply_text('Hey, my name is.\nSend me the password')
		return STATE_UNAUTH

	upd.message.reply_text('Hey, my name is. We need to set up the password first.\nSend it to me:')
	return STATE_PASSWORD_SETUP

# Handles messages containing password in UNAUTH state (need to be compared with saved hash)
def password_auth_received(upd, ctx):
	chat_id = upd.message.chat_id

	# If already authorized then just switch to IDLE
	if is_authorized(ctx):
		upd.message.reply_text('You are already authorized')
		return STATE_IDLE

	# If you are here, then chat is not authorized.
	if chat_exist(chat_id):

# Handles messages containing password in SETUP state (need to be created new one)
def password_set_received(upd, ctx):
	chat_id = upd.message.chat_id

	pass

# Temporary handler which just echoes what it receives
def debug_repeat(upd, ctx):
	upd.message.reply_text('You just sent: {0}'.format(upd.message.text))

#####################################################
############ Ordinary functions section #############
#####################################################

def is_authorized(ctx):
	return 'authorized' in ctx.chat_data \
			and ctx.chat_data['authorized'] is not None \
			and timestamp_now() - ctx.chat_data['authorized'] <= DEFAULT_UNAUTH_TIMER