from django.db import close_old_connections
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from authn.providers.telegram import TelegramAuthError, confirm


async def command_start(update: Update, context: CallbackContext) -> None:
    close_old_connections()
    try:
        code = (context.args or [None])[0]
        if not code:
            await update.effective_chat.send_message(
                "Откройте бота по ссылке со страницы входа на Базу. "
                "Просто так я не знаю, кого привязывать.",
                parse_mode=ParseMode.HTML,
            )
            return

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Войти в Базу", callback_data=f"link:{code}"),
        ]])
        await update.effective_chat.send_message(
            "Нажмите кнопку, чтобы войти в Базу.",
            reply_markup=keyboard,
        )
    finally:
        close_old_connections()


async def confirm_callback(update: Update, context: CallbackContext) -> None:
    close_old_connections()
    try:
        query = update.callback_query
        await query.answer()
        code = (query.data or "").split(":", 1)[-1]
        tg = query.from_user
        data = {
            "id": tg.id,
            "username": tg.username,
            "first_name": tg.first_name,
            "last_name": tg.last_name,
            "language_code": tg.language_code,
        }
        try:
            text, url = confirm(code, data)
        except TelegramAuthError as ex:
            await query.edit_message_text(ex.message)
            return

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Открыть сайт", url=url),
            ]]),
        )
    finally:
        close_old_connections()
