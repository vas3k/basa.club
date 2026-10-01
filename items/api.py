from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from common import ratings
from items.models import Item, ItemVote


@require_POST
def upvote_item(request, item_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Нужно войти"}, status=401)

    item = get_object_or_404(
        Item.objects.select_related("author"),
        pk=item_id,
        visibility__in=[Item.VISIBILITY_VISIBLE, Item.VISIBILITY_LINK_ONLY],
    )
    if item.author_id == request.user.pk:
        return JsonResponse({"error": "Нельзя голосовать за свое"}, status=403)

    _, created = ItemVote.upvote(request.user, item, request)
    if created:
        ratings.apply_item_vote(item, +1)
    return JsonResponse({"upvotes": item.upvotes, "voted": True})


@require_POST
def retract_item_vote(request, item_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Нужно войти"}, status=401)

    item = get_object_or_404(
        Item.objects.select_related("author"),
        pk=item_id,
        visibility__in=[Item.VISIBILITY_VISIBLE, Item.VISIBILITY_LINK_ONLY],
    )
    if ItemVote.retract(request.user, item):
        ratings.apply_item_vote(item, -1)
    return JsonResponse({"upvotes": item.upvotes, "voted": False})
