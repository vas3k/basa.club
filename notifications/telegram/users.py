from django.utils import timezone

from notifications.telegram.common import render_html_message, send_telegram_message
from users.models import User


def send_telegram_user_logged_in(user_id):
    user = User.objects.filter(pk=user_id).first()
    if not user or not user.telegram_id:
        return
    send_telegram_message(user.telegram_id, "✅ <b>Ура! Вы успешно вошли в Базу</b>")


def send_telegram_user_banned(user_id, reason, comment, until, is_permanent):
    user = User.objects.filter(pk=user_id).first()
    if not user or not user.telegram_id:
        return
    left = until - timezone.now()
    send_telegram_message(user.telegram_id, render_html_message(
        "notifications/telegram/messages/user_banned.html",
        reason=reason,
        comment=comment,
        is_permanent=is_permanent,
        days=left.days,
        hours=left.seconds // 3600,
        minutes=(left.seconds % 3600) // 60,
    ))
