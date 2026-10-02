from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from comments.models import Comment, CommentVote
from common import counters
from common.request import parse_ip_address, parse_useragent


@require_POST
def upvote_comment(request, comment_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Нужно войти"}, status=401)

    comment = get_object_or_404(
        Comment.objects.select_related("item", "author"),
        pk=comment_id,
    )
    if comment.author_id == request.user.pk:
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
    if created:
        counters.comment_upvoted(comment)

    return JsonResponse({"upvotes": comment.upvotes, "voted": True})


@require_POST
def retract_comment_vote(request, comment_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Нужно войти"}, status=401)

    comment = get_object_or_404(
        Comment.objects.select_related("item", "author"),
        pk=comment_id,
    )
    deleted, _ = CommentVote.objects.filter(user=request.user, comment=comment).delete()
    if deleted:
        counters.comment_unvoted(comment)

    return JsonResponse({"upvotes": comment.upvotes, "voted": False})
