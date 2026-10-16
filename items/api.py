from django.conf import settings
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from authn.helpers import api_login_required
from counters import counters
from common.request import parse_ip_address, parse_useragent
from common.templatetags.text import rating as format_rating
from items.models import Item, ItemVote


@api_login_required
@require_POST
def upvote_item(request, item_id):
    item = get_object_or_404(
        Item.objects.select_related("author"),
        id=item_id,
        visibility__in=[Item.VISIBILITY_VISIBLE, Item.VISIBILITY_LINK_ONLY],
    )
    if item.author_id == request.user.id:
        return JsonResponse({"error": "Нельзя голосовать за свое"}, status=403)

    already_voted = ItemVote.objects.filter(user=request.user, item=item).exists()
    if not already_voted and not ItemVote.check_rate_limits(request.user):
        return JsonResponse({
            "error": f"Можно оставить не больше {settings.ITEM_VOTE_RATE_LIMIT} голосов за посты за сутки",
        }, status=429)

    _, created = ItemVote.objects.get_or_create(
        user=request.user,
        item=item,
        defaults={
            "ipaddress": parse_ip_address(request),
            "useragent": parse_useragent(request),
        },
    )
    if created:
        counters.item_upvoted(item)

    item.refresh_from_db(fields=["rating"])
    return JsonResponse({"rating": format_rating(item.rating), "voted": True})


@api_login_required
@require_POST
def retract_item_vote(request, item_id):
    item = get_object_or_404(
        Item.objects.select_related("author"),
        id=item_id,
        visibility__in=[Item.VISIBILITY_VISIBLE, Item.VISIBILITY_LINK_ONLY],
    )
    vote = ItemVote.objects.filter(user=request.user, item=item).first()
    if vote and not vote.is_retractable():
        return JsonResponse({
            "error": f"Голос можно забрать только первые {settings.VOTE_RETRACT_PERIOD.days} дней",
        }, status=403)

    deleted = 0
    if vote:
        vote.delete()
        deleted = 1

    if deleted and item.author_id == request.user.id:
        Item.objects.filter(id=item.id).update(upvotes=F("upvotes") - 1)
    elif deleted:
        counters.item_unvoted(item)

    item.refresh_from_db(fields=["rating"])
    return JsonResponse({"rating": format_rating(item.rating), "voted": False})
