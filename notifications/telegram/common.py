import logging

import requests
from django.conf import settings
from django.template import loader

log = logging.getLogger(__name__)

TEXT_LIMIT = 4096
CAPTION_LIMIT = 1024
TELEGRAM_API = "https://api.telegram.org/bot"

BOT_BLOCKED = (
    "bot was blocked by the user",
    "user is deactivated",
    "bot can't initiate conversation with a user",
    "chat not found",
)


def render_html_message(template, **data):
    return loader.get_template(template).render({
        **data,
        "settings": settings,
    })


def send_telegram_message(chat_id, text, reply_markup=None):
    if not chat_id or not text:
        return None
    payload = {
        "chat_id": chat_id,
        "text": text[:TEXT_LIMIT],
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True},
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return telegram_api("sendMessage", payload)


def send_telegram_photo(chat_id, photo, caption, reply_markup=None):
    if not chat_id or not photo:
        return None
    payload = {
        "chat_id": chat_id,
        "photo": photo,
        "caption": (caption or "")[:CAPTION_LIMIT],
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return telegram_api("sendPhoto", payload)


def telegram_api(method, payload):
    token = settings.TELEGRAM_TOKEN or ""
    if not token or token.endswith("MOCK_TOKEN_REPLACE_ME"):
        log.warning("No telegram token. Skipping")
        return None

    log.info("Telegram: %s to %s", method, payload.get("chat_id"))
    try:
        response = requests.post(f"{TELEGRAM_API}{token}/{method}", json=payload, timeout=15)
    except requests.RequestException:
        log.exception("Telegram request failed: %s", method)
        raise

    try:
        data = response.json()
    except ValueError:
        data = {}

    if data.get("ok"):
        return data

    description = str(data.get("description") or response.text or "")
    log.warning("Telegram error: %s", description)
    if response.status_code >= 500 or response.status_code == 429:
        response.raise_for_status()
    remember_blocked_chat(payload.get("chat_id"), description)
    return None


def remember_blocked_chat(chat_id, description):
    marker = next((marker for marker in BOT_BLOCKED if marker in description.lower()), None)
    if not marker or not chat_id:
        return
    from users.models import User

    user = User.objects.filter(telegram_id=str(chat_id)).first()
    if not user or (user.metadata or {}).get("telegram_problem") == marker:
        return
    metadata = dict(user.metadata or {})
    metadata["telegram_problem"] = marker
    user.metadata = metadata
    user.save(update_fields=["metadata"])
