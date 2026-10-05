import logging

from django.utils import timezone

from notifications.telegram.common import render_html_message, send_telegram_message

log = logging.getLogger(__name__)


def user_banned(user, *, reason, comment, until, is_permanent):
    if not user.telegram_id:
        return
    left = until - timezone.now()
    send_telegram_message(user.telegram_id, render_html_message(
        "user_banned.html",
        reason=reason,
        comment=comment,
        is_permanent=is_permanent,
        days=left.days,
        hours=left.seconds // 3600,
        minutes=(left.seconds % 3600) // 60,
    ))
