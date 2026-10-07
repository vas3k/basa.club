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
        pk=item_id,
        visibility__in=[Item.VISIBILITY_VISIBLE, Item.VISIBILITY_LINK_ONLY],
    )
    if item.author_id == request.user.pk:
        return JsonResponse({"error": "Нельзя голосовать за свое"}, status=403)

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

    return JsonResponse({"rating": format_rating(item.rating), "voted": True})


@api_login_required
@require_POST
def retract_item_vote(request, item_id):
    item = get_object_or_404(
        Item.objects.select_related("author"),
        pk=item_id,
        visibility__in=[Item.VISIBILITY_VISIBLE, Item.VISIBILITY_LINK_ONLY],
    )
    deleted, _ = ItemVote.objects.filter(user=request.user, item=item).delete()
    if deleted:
        counters.item_unvoted(item)

    return JsonResponse({"rating": format_rating(item.rating), "voted": False})
