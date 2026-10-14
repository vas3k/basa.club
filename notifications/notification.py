from django_q.tasks import async_task

from notifications.subscriptions import subscribers_for_item
from notifications.telegram.base import send_telegram_base_new_item
from notifications.telegram.comments import send_telegram_user_new_comment
from notifications.telegram.items import send_telegram_user_new_item
from notifications.telegram.moderation import send_telegram_admin_new_flag, send_telegram_admin_new_item
from notifications.telegram.users import send_telegram_user_banned, send_telegram_user_logged_in


def item_created(item):
    async_task(send_telegram_admin_new_item, item.id)
    async_task(send_telegram_base_new_item, item.id)
    async_task(send_telegram_user_new_item, item.id, [s.id for s in subscribers_for_item(item)])


def comment_created(comment):
    async_task(send_telegram_user_new_comment, comment.id)


def flag_created(flag):
    async_task(send_telegram_admin_new_flag, flag.id)


def user_logged_in(user):
    async_task(send_telegram_user_logged_in, user.id)


def user_banned(user, *, reason, comment, until, is_permanent):
    async_task(send_telegram_user_banned, user.id, reason, comment or "", until, is_permanent)
