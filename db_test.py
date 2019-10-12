import db_handler as dbh

dbh.create_chat_if_not_exist(12, 'adf')
dbh.create_record(12, 'data1')
dbh.create_record(12, 'data2')
print (dbh.delete_all(12))