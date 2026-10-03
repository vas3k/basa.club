import logging
import threading

from django.conf import settings
from django.db import connections, transaction
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from items.models import Item
from notifications.subscriptions import subscribers_for_item, subscription_kind
from notifications.telegram.bot import telegram_configured
from notifications.telegram.common import (
    CAPTION_LIMIT,
    render_html_message,
    send_telegram_message,
    send_telegram_photo,
)

log = logging.getLogger(__name__)

TEMPLATES = {
    "global": "new_item_global.html",
    "country": "new_item_country.html",
    "city": "new_item_city.html",
    "category": "new_item_category.html",
    "query": "new_item_query.html",
}


def item_created(item):
    """Tell subscribers that an item just entered the feed.

    Called when an item is published, including a draft that is published later.
    Editing an item that is already listed does not call this.
    """
    if not item.is_listed:
        return
    item_id = item.pk

    def start():
        thread = threading.Thread(target=_deliver, args=(item_id,), name="notify-item", daemon=True)
        thread.start()

    transaction.on_commit(start)


def _deliver(item_id):
    try:
        item = Item.objects.select_related(
            "category", "subcategory", "country", "city", "author",
        ).filter(pk=item_id).first()
        if not item or not item.is_listed:
            return

        subscriptions = subscribers_for_item(item)
        if not telegram_configured():
            log.info("telegram is not configured, %s subscribers for item %s", len(subscriptions), item_id)
            return

        for subscription in subscriptions:
            _send(subscription, item)
        log.info("notified %s subscribers about item %s", len(subscriptions), item_id)
    except Exception:
        log.exception("failed to notify about item %s", item_id)
    finally:
        connections.close_all()


def _send(subscription, item):
    kind = subscription_kind(subscription)
    text = render_html_message(TEMPLATES[kind], item=item, subscription=subscription)
    markup = _markup(item, subscription)
    image = _image(item)
    if image and len(text) <= CAPTION_LIMIT:
        send_telegram_photo(subscription.user.telegram_id, image, text, reply_markup=markup)
        return
    send_telegram_message(subscription.user.telegram_id, text, reply_markup=markup)


def _markup(item, subscription):
    row = []
    url = settings.APP_HOST.rstrip("/") + item.get_absolute_url()
    if url.startswith("https://"):
        row.append(InlineKeyboardButton("Открыть", url=url))
    row.append(InlineKeyboardButton("Отписаться от таких", callback_data=f"unsub:{subscription.id}"))
    return InlineKeyboardMarkup([row])


def _image(item):
    images = item.images or []
    if not images or not isinstance(images[0], dict):
        return None
    url = images[0].get("image") or ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return None
