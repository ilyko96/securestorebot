# User turn states for ConversationHandler
STATE_START, \
STATE_IDLE, \
STATE_TYPING_PASSWORD, \
STATE_CHOOSE_PASSWORD_ACTION, \
STATE_TYPING_RECORD,\
STATE_CONFIRMING_RECORD,\
STATE_BROWSING = range(7)

# Modes for ctx.user_data['password_mode'] flag
MODE_PWD_SET,\
MODE_PWD_TEST,\
MODE_PWD_AUTHORIZED = range(3)

# Names of keyboard buttons
BTN_PWD_STRONGER =	'Create stronger'
BTN_PWD_LEAVEWEAK =	'Leave weak'
BTN_PWD_TRYAGAIN =	'Try again'
BTN_PWD_STARTOVER =	'Start over'
BTN_RECORD =		'Add record'
BTN_BROWSE =		'Browse'
BTN_PWD_CHANGE =	'Change password'
BTN_FINISH =		'Finish'
BTN_PWD_NEW =		'Create new password'
BTN_SETTINGS =		'Settings'
BTN_LOGOUT =		'Log out'
BTN_START =			'Start'
BTN_RECORD_SAVE =	'Save'
BTN_RECORD_CANCEL =	'Cancel'
BTN_BROWSE_PREV = 	'<< Previous'
BTN_BROWSE_NEXT = 	'Next >>'
BTN_BROWSE_BACK = 	'Back'

# Message that needs to be entered by user in order to destroy all data
CONSCIOUS_CONFIRMATION_MSG = 'Consciously I remove all {0} records'

# Parameters that can be set up in [Settings]
DEFAULT_UNAUTH_TIMER =		30		# Amount of seconds after which bot unauthorizes user
DEFAULT_CLEAR_ON_LOGOUT =	True	# If bot should delete history on logout
DEFAULT_CLEAR_ON_ALARM =	False	# If bot should delete history on unauthorization alarm

BROWSE_PAGE_LIMIT = 7 # Number of records that are being displayed on [Browse] button