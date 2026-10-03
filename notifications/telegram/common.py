import logging

from django.conf import settings
from django.template import loader
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram import LinkPreviewOptions

from notifications.telegram.bot import bot

log = logging.getLogger(__name__)

TEXT_LIMIT = 4096
CAPTION_LIMIT = 1024


def send_telegram_message(chat_id, text, reply_markup=None):
    if not bot:
        log.warning("No telegram token. Skipping")
        return None
    if not chat_id or not text:
        log.warning("No chat id or text. Skipping")
        return None

    log.info("Telegram: sending message to %s, starting with %s", chat_id, text[:40])
    try:
        return bot.send_message(
            chat_id=chat_id,
            text=text[:TEXT_LIMIT],
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
            reply_markup=reply_markup,
        )
    except TelegramError as ex:
        log.warning("Telegram error: %s", ex)
        return None


def send_telegram_photo(chat_id, photo, caption, reply_markup=None):
    if not bot:
        log.warning("No telegram token. Skipping")
        return None
    if not chat_id or not photo:
        return None

    log.info("Telegram: sending photo to %s", chat_id)
    try:
        return bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=(caption or "")[:CAPTION_LIMIT],
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    except TelegramError as ex:
        log.warning("Telegram error: %s", ex)
        return None


def render_html_message(template, **data):
    rendered = loader.get_template(f"messages/{template}")
    return rendered.render({
        **data,
        "settings": settings,
    })
