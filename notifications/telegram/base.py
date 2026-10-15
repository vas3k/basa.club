from django.conf import settings

from items.models import Item
from notifications.telegram.common import render_html_message, send_telegram_message


def send_telegram_base_new_item(item_id):
    chat_id = settings.TELEGRAM_BASE_CHAT_ID
    if not chat_id:
        return
    item = Item.objects.select_related(
        "category", "subcategory", "country", "city", "author",
    ).filter(id=item_id).first()
    if not item:
        return
    send_telegram_message(chat_id, render_html_message("notifications/telegram/base/new_item.html", item=item))
