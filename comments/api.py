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
    deleted, _ = CommentVote.objects.filter(user=request.user, comment=comment).delete()
    if deleted and request.user.id in {comment.author_id, comment.item.author_id}:
        Comment.objects.filter(id=comment.id).update(upvotes=F("upvotes") - 1)
    elif deleted:
        counters.comment_unvoted(comment)

    comment.refresh_from_db(fields=["upvotes"])
    return JsonResponse({"upvotes": comment.upvotes, "voted": False})
