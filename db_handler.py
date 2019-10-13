from peewee import *
from util import *
import logging, datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					level=logging.INFO)
# logger = logging.getLogger(__name__)
logger = logging.getLogger('peewee')
# logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)

db = SqliteDatabase('database.db')

class BaseModel(Model):
	class Meta:
		database = db

class Chat(BaseModel):
	chat_id = IntegerField(unique=True)
	password = TextField(null=True)
	inactive_time = IntegerField(default=600)

class Record(BaseModel):
	chat_uid = ForeignKeyField(Chat)
	timestamp = DateField()
	data = TextField(null=True)
	data_size = IntegerField()

db.create_tables([Chat, Record])

# TODO: get rid of repetitive code (always checking chat_id and len()!)!!!
# Creates new chat entry and returns 1 if created successfully, 0 - if already exists, other - error
def create_chat_if_not_exist(chat_id, password=None):
	chats = Chat.select().where(Chat.chat_id == chat_id)
	if len(chats) == 0:
		return Chat(chat_id=chat_id, password=password).save()
	elif len(chats) > 1:
		logger.warning('{1} duplicates for chat_id=\'{0}\' exist! New entry has not been created'.format(chat_id, len(chats) - 1))
		return len(chats)
	return 0

# TODO: delete multiple in case of error
# Deletes chat entry and returns 1 if deletes successfully, 0 - if no chat found, other - error
def delete_chat(chat_id):
	chats = Chat.select().where(Chat.chat_id == chat_id)
	if len(chats) == 1:
		return chats.get().delete_instance()
	elif len(chats) > 1:
		logger.warning('{1} duplicates for chat_id=\'{0}\' exist! Entry has not been deleted'.format(chat_id, len(chats) - 1))
		return len(chats)
	return 0

# Updates (or creates new) entry with new password and returns 1 - if success, other - error
def set_password(chat_id, password):
	chat = Chat.select().where(Chat.chat_id == chat_id)
	if len(chat) == 0:
		return Chat(chat_id=chat_id, password=password).save()
	elif len(chat) == 1:
		chat = chat.get()
		chat.password = password
		return chat.save()
	logger.warning('{1} duplicates for chat_id=\'{0}\' exist! Entry has not been updated'.format(chat_id, len(chat) - 1))
	return len(chat)

# TODO: probably manage ourselves by deleting duplicates
# Retrieves password-hash and returns it in case of succes, None - if error
def get_password(chat_id):
	chat = Chat.select().where(Chat.chat_id == chat_id)
	if len(chat) == 0:
		return None
	elif len(chat) > 1:
		logger.warning('{1} duplicates for chat_id=\'{0}\' exist! Ignored'.format(chat_id, len(chat) - 1))
	return chat.get().password

# TODO: probably manage ourselves by deleting duplicates
# Creates record (first checking chat_id for existance and creating if absent) and returns 1 - on success, 0 - otherwise
def create_record(chat_id, data):
	chat = Chat.select().where(Chat.chat_id == chat_id)
	if len(chat) == 0:
		logger.warning('Chat with chat_id=\'{0}\' could not be found!'
					   'Record will be saved, chat will be created, but no password stored!'.format(chat_id))
		create_chat_if_not_exist(chat_id)
	elif len(chat) > 1:
		logger.warning('{1} duplicates for chat_id=\'{0}\' exist!'
					   'Record will be saved for chat_uid=\'{2}\''.format(chat_id, len(chat) - 1, chat.id))

	record = Record(chat_uid=chat.get(), timestamp=timestamp_now(), data=data, data_size=len(data))
	return record.save()

# TODO: probably manage ourselves by deleting duplicates
# Deletes all data connected with given chat_id. returns number of deletions from tables (chats, records)
def delete_all(chat_id):
	chat = Chat.select(Chat.id).where(Chat.chat_id == chat_id)
	if len(chat) == 0:
		logger.warning('Chat with chat_id=\'{0}\' could not be found! Data has not been not deleted!')
		return (0, 0)
	elif len(chat) > 1:
		logger.warning('{1} duplicates for chat_id=\'{0}\' exist!')

	records = Record.delete().where(Record.chat_uid == chat).execute()
	chat = Chat.delete().where(Chat.chat_id == chat_id).execute()
	return (chat, records)

# TODO: probably manage ourselves by deleting duplicates
# Returns meta-info on all records for given chat_id
def get_records_overview(chat_id, limit=None):
	chat = Chat.select(Chat.id).where(Chat.chat_id == chat_id)
	if len(chat) == 0:
		logger.warning('Chat with chat_id=\'{0}\' could not be found! Creating new.')
		create_chat_if_not_exist(chat_id)
	elif len(chat) > 1:
		logger.warning('{1} duplicates for chat_id=\'{0}\' exist!')

	chat = Chat.select(Chat.id).where(Chat.chat_id == chat_id)
	if len(chat) == 0:
		logger.warning('Chat with chat_id=\'{0}\' could not be found even after creating! Probably DB is not available.')
		return None

	records = Record.select(Record.id, Record.timestamp, Record.data_size).where(Record.chat_uid == chat).execute()

	return [{
		'uid': r.id,
		'timestamp': r.timestamp,
		'size': r.data_size
	} for r in records]