import logging

from django.db import close_old_connections
from telegram import InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from notifications.subscriptions import unsubscribe

log = logging.getLogger(__name__)


async def unsubscribe_callback(update: Update, context: CallbackContext) -> None:
    close_old_connections()
    try:
        query = update.callback_query
        subscription_id = (query.data or "").split(":", 1)[-1]
        result = unsubscribe(subscription_id, query.from_user.id)
        if result == "forbidden":
            await query.answer("Это не ваша подписка", show_alert=True)
            return
        if result == "removed":
            await query.answer("Ок, больше не присылаем новое из этого раздела")
        else:
            await query.answer("Вы уже отписались от этого раздела")

        await _drop_unsubscribe_button(query)
    finally:
        close_old_connections()


async def _drop_unsubscribe_button(query):
    markup = query.message.reply_markup if query.message else None
    rows = []
    if markup:
        for row in markup.inline_keyboard:
            kept = [button for button in row if not (button.callback_data or "").startswith("unsub:")]
            if kept:
                rows.append(kept)
                
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))
    except Exception:
        log.exception("failed to update unsubscribe keyboard")
