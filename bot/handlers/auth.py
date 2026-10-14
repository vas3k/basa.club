from django.db import close_old_connections
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from authn.providers.telegram import TelegramAuthError, confirm
from bot.config import BOT_PAGE_URL


async def command_start(update: Update, context: CallbackContext) -> None:
    close_old_connections()
    try:
        code = (context.args or [None])[0]
        if not code:
            await update.effective_chat.send_message(
                "Откройте страницу привязки на Базе и нажмите кнопку. "
                "Просто так я не знаю, кого привязывать.\n"
                f"{BOT_PAGE_URL}"
            )
            return

        tg = update.effective_user
        if not tg:
            await update.effective_chat.send_message("Не получилось прочитать профиль Telegram. Попробуйте ещё раз.")
            return

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
            await update.effective_chat.send_message(ex.message)
            return

        await update.effective_chat.send_message(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Войти в Базу", url=url),
            ]]),
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
                InlineKeyboardButton("Войти в Базу", url=url),
            ]]),
        )
    finally:
        close_old_connections()
