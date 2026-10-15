from django.conf import settings

from items.models import Item
from notifications.models import Subscription
from notifications.subscriptions import subscription_kind
from notifications.telegram.common import (
    CAPTION_LIMIT,
    render_html_message,
    send_telegram_message,
    send_telegram_photo,
)


def send_telegram_user_new_item(item_id, subscription_ids):
    item = Item.objects.select_related(
        "category", "subcategory", "country", "city", "author",
    ).filter(id=item_id).first()
    if not item or not item.is_listed or not subscription_ids:
        return

    subscriptions = Subscription.objects.select_related(
        "user", "country", "city", "category",
    ).filter(id__in=subscription_ids)

    url = settings.APP_HOST.rstrip("/") + item.get_absolute_url()
    images = item.images or []
    image = None
    if images and isinstance(images[0], dict):
        candidate = images[0].get("image") or ""
        if candidate.startswith("http://") or candidate.startswith("https://"):
            image = candidate

    for subscription in subscriptions:
        if not subscription.user.telegram_id:
            continue

        text = render_html_message(
            f"notifications/telegram/messages/new_item_{subscription_kind(subscription)}.html",
            item=item,
            subscription=subscription,
        )
        buttons = []
        if url.startswith("https://"):
            buttons.append({"text": "Открыть", "url": url})
        buttons.append({"text": "Отписаться от таких", "callback_data": f"unsub:{subscription.id}"})
        markup = {"inline_keyboard": [buttons]}

        chat_id = subscription.user.telegram_id
        if image and len(text) <= CAPTION_LIMIT:
            if send_telegram_photo(chat_id, image, text, reply_markup=markup):
                continue
        send_telegram_message(chat_id, text, reply_markup=markup)
