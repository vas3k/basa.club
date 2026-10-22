from comments.models import Comment
from django.template.defaultfilters import truncatechars_html
from notifications.telegram.common import TEXT_LIMIT, render_html_message, send_telegram_message

BODY_LIMIT = TEXT_LIMIT - 1800


def send_telegram_user_new_comment(comment_id):
    comment = Comment.objects.select_related(
        "author", "item", "item__author", "reply_to", "reply_to__author",
    ).filter(id=comment_id).first()
    if not comment or comment.item.deleted_at:
        return

    if comment.reply_to and comment.reply_to.deleted_at:
        return

    recipients = [comment.item.author]
    if comment.reply_to_id and comment.reply_to:
        recipients = [comment.reply_to.author, comment.item.author]

    vibe = comment.reply_to if comment.reply_to_id and comment.reply_to else comment

    seen = {comment.author_id}
    for user in recipients:
        if not user or user.deleted_at or user.is_banned or not user.telegram_id or user.id in seen:
            continue
        if comment.item.visibility == "draft" and user.id != comment.item.author_id and not user.is_moderator:
            continue
        seen.add(user.id)
        text_limit = BODY_LIMIT
        while True:
            text = render_html_message(
                "notifications/telegram/messages/new_comment.html",
                comment=comment,
                vibe_label=vibe.get_vibe_display() or "",
                is_reply=bool(comment.reply_to_id),
                is_parent_author=bool(comment.reply_to and user.id == comment.reply_to.author_id),
                text_limit=text_limit,
            )
            if truncatechars_html(text, TEXT_LIMIT) == text or text_limit <= 100:
                break
            text_limit = max(100, text_limit // 2)

        send_telegram_message(user.telegram_id, text)
