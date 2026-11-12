from django.template.defaultfilters import truncatechars_html

from items.models import Item
from notifications.subscriptions import subscribers_for_item
from notifications.telegram.common import (
    TEXT_LIMIT,
    render_html_message,
    send_telegram_message,
)


def send_telegram_user_new_item(item_id, subscription_ids):
    item = Item.objects.select_related(
        "category", "subcategory", "country", "city", "author",
    ).filter(id=item_id).first()
    if not item or not item.is_listed or not subscription_ids or item.author.deleted_at or item.author.is_banned:
        return

    subscriptions = subscribers_for_item(item, subscription_ids=subscription_ids)

    for subscription in subscriptions:
        if not subscription.user.telegram_id:
            continue

        text = render_html_message(
            "notifications/telegram/messages/new_item.html",
            item=item,
            subscription=subscription,
            show_unsibscribe_footer=True,
        )
        body, footer = text.rsplit("\n\n", 1)
        text = truncatechars_html(body, TEXT_LIMIT - len(footer) - 2) + "\n\n" + footer

        chat_id = subscription.user.telegram_id
        send_telegram_message(chat_id, text)
