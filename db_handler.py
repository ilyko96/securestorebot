from peewee import *
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
	password = TextField()

class Record(BaseModel):
	chat_uid = ForeignKeyField(Chat)
	timestamp = DateField()
	data = TextField(null=True)

db.create_tables([Chat, Record])

# Creates new chat entry and returns 1 if created successfully, 0 - if already exists, other - error
def create_chat(chat_id, password=''):
	chats = Chat.select().where(Chat.chat_id == chat_id)
	if len(chats) == 0:
		return Chat(chat_id=chat_id, password=password).save()
	elif len(chats) > 1:
		logger.warning('{1} duplicates for chat_id=\'{0}\' exists! New entry has not been created'.format(chat_id, len(chats) - 1))
		return len(chats)
	return 0

# Deletes chat entry and returns 1 if deletes successfully, 0 - if no chat found, other - error
def delete_chat(chat_id):
	chats = Chat.select().where(Chat.chat_id == chat_id)
	if len(chats) == 1:
		return chats.get().delete_instance()
	elif len(chats) > 1:
		logger.warning('{1} duplicates for chat_id=\'{0}\' exists! Entry has not been deleted'.format(chat_id, len(chats) - 1))
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
	logger.warning('{1} duplicates for chat_id=\'{0}\' exists! Entry has not been updated'.format(chat_id, len(chat) - 1))
	return len(chat)

# Retrieves password-hash and returns it in case of succes, None - if error
def get_password(chat_id):
	chat = Chat.select().where(Chat.chat_id == chat_id)
	if len(chat) == 0:
		return None
	elif len(chat) == 1:
		return chat.get().password
	return None