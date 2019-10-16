import datetime

# Returns current timestamp as integer (number of seconds utc)
def timestamp_now():
	return int(datetime.datetime.timestamp(datetime.datetime.now()))

# Takes integer in utc and returns formated string of this datetime
def timestamp_format(tstmp: int):
	dt = datetime.datetime.fromtimestamp(tstmp)
	return dt.strftime("%m/%d/%Y %H:%M:%S")