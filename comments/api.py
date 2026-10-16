from django.conf import settings
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from authn.helpers import api_login_required
from comments.models import Comment, CommentVote
from counters import counters
from common.request import parse_ip_address, parse_useragent


@api_login_required
@require_POST
def upvote_comment(request, comment_id):
    comment = get_object_or_404(
        Comment.objects.select_related("item", "author"),
        id=comment_id,
    )
    if comment.author_id == request.user.id:
        return JsonResponse({"error": "Нельзя голосовать за свое"}, status=403)

    already_voted = CommentVote.objects.filter(user=request.user, comment=comment).exists()
    if not already_voted and not CommentVote.check_rate_limits(request.user):
        return JsonResponse({
            "error": f"Можно оставить не больше {settings.COMMENT_VOTE_RATE_LIMIT} голосов за комментарии за сутки",
        }, status=429)

    _, created = CommentVote.objects.get_or_create(
        user=request.user,
        comment=comment,
        defaults={
            "item": comment.item,
            "ipaddress": parse_ip_address(request),
            "useragent": parse_useragent(request),
        },
    )
    if created and comment.item.author_id == request.user.id:
        Comment.objects.filter(id=comment.id).update(upvotes=F("upvotes") + 1)
    elif created:
        counters.comment_upvoted(comment)

    comment.refresh_from_db(fields=["upvotes"])
    return JsonResponse({"upvotes": comment.upvotes, "voted": True})


@api_login_required
@require_POST
def retract_comment_vote(request, comment_id):
    comment = get_object_or_404(
        Comment.objects.select_related("item", "author"),
        id=comment_id,
    )
    vote = CommentVote.objects.filter(user=request.user, comment=comment).first()
    if vote and not vote.is_retractable():
        return JsonResponse({
            "error": f"Голос можно забрать только первые {settings.VOTE_RETRACT_PERIOD.days} дней",
        }, status=403)

    deleted = 0
    if vote:
        vote.delete()
        deleted = 1
    if deleted and request.user.id in {comment.author_id, comment.item.author_id}:
        Comment.objects.filter(id=comment.id).update(upvotes=F("upvotes") - 1)
    elif deleted:
        counters.comment_unvoted(comment)

    comment.refresh_from_db(fields=["upvotes"])
    return JsonResponse({"upvotes": comment.upvotes, "voted": False})
