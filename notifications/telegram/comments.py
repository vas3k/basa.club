from comments.models import Comment
from notifications.telegram.common import TEXT_LIMIT, render_html_message, send_telegram_message

BODY_LIMIT = TEXT_LIMIT - 800


def send_telegram_user_new_comment(comment_id):
    comment = Comment.objects.select_related(
        "author", "item", "item__author", "reply_to", "reply_to__author",
    ).filter(pk=comment_id).first()
    if not comment:
        return

    recipients = [comment.item.author]
    if comment.reply_to_id and comment.reply_to:
        recipients = [comment.reply_to.author, comment.item.author]

    vibe = comment.reply_to if comment.reply_to_id and comment.reply_to else comment
    text = render_html_message(
        "messages/new_comment.html",
        comment=comment,
        vibe_label=vibe.get_vibe_display() or "",
        is_reply=bool(comment.reply_to_id),
        text_limit=BODY_LIMIT,
    )

    seen = {comment.author_id}
    for user in recipients:
        if not user or not user.telegram_id or user.pk in seen:
            continue
        seen.add(user.pk)
        send_telegram_message(user.telegram_id, text)
