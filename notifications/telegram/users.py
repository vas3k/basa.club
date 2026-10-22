from django.utils import timezone

from bot.handlers.help import HELP_MESSAGE
from notifications.telegram.common import render_html_message, send_telegram_message
from users.models import User


def send_telegram_user_logged_in(user_id):
    user = User.objects.filter(id=user_id).first()
    if not user or not user.telegram_id or user.is_banned:
        return
    send_telegram_message(
        user.telegram_id,
        render_html_message(
            "notifications/telegram/messages/user_logged_in.html",
            user=user,
            help_message=HELP_MESSAGE,
        ),
    )


def send_telegram_user_banned(user_id, reason, comment, until, is_permanent):
    user = User.objects.filter(id=user_id).first()
    if not user or not user.telegram_id or not user.is_banned or user.is_banned_until != until:
        return
    total_minutes = max(0, int((until - timezone.now()).total_seconds() // 60))
    days, remaining_minutes = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(remaining_minutes, 60)
    send_telegram_message(user.telegram_id, render_html_message(
        "notifications/telegram/messages/user_banned.html",
        reason=reason,
        comment=comment,
        is_permanent=is_permanent,
        until=until,
        days=days,
        hours=hours,
        minutes=minutes,
    ))
