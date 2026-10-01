from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from comments.models import Comment, CommentVote
from common import ratings


@require_POST
def upvote_comment(request, comment_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Нужно войти"}, status=401)

    comment = get_object_or_404(
        Comment.objects.select_related("item", "author"),
        pk=comment_id,
        deleted_at__isnull=True,
    )
    if comment.author_id == request.user.pk:
        return JsonResponse({"error": "Нельзя голосовать за свое"}, status=403)

    _, created = CommentVote.upvote(request.user, comment, request)
    if created:
        ratings.apply_comment_vote(comment, +1)
    return JsonResponse({"upvotes": comment.upvotes, "voted": True})


@require_POST
def retract_comment_vote(request, comment_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Нужно войти"}, status=401)

    comment = get_object_or_404(
        Comment.objects.select_related("item", "author"),
        pk=comment_id,
        deleted_at__isnull=True,
    )
    if CommentVote.retract(request.user, comment):
        ratings.apply_comment_vote(comment, -1)
    return JsonResponse({"upvotes": comment.upvotes, "voted": False})
