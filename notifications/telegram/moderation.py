from django.conf import settings

from complaints.models import Flag
from items.models import Item
from notifications.telegram.common import render_html_message, send_telegram_message


def send_telegram_admin_new_item(item_id):
    chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    if not chat_id:
        return
    item = Item.objects.select_related(
        "category", "subcategory", "country", "city", "author",
    ).filter(id=item_id).first()
    if not item:
        return
    send_telegram_message(chat_id, render_html_message("notifications/telegram/moderation/new_item.html", item=item))


def send_telegram_admin_new_flag(flag_id):
    chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    if not chat_id:
        return
    flag = Flag.objects.select_related("user", "item").filter(id=flag_id).first()
    if not flag:
        return
    send_telegram_message(chat_id, render_html_message("notifications/telegram/moderation/new_flag.html", flag=flag))
