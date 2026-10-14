HELP_MESSAGE = (
    "Пришлите рекомендацию или перешлите сообщение из чата — я добавлю карточку в Базу. "
    "В других чатах ответьте /add на сообщение. После команды можно дописать свой комментарий."
)


async def command_help(update, context):
    await update.effective_chat.send_message(HELP_MESSAGE)
