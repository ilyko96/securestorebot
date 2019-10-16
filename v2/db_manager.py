
def chat_exist(ctx, chat_id):
	return chat_id in ctx.chat_data and ctx.chat_data[chat_id] is not None