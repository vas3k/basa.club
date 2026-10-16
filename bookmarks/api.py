from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from authn.helpers import api_login_required
from bookmarks.models import Bookmark
from counters import counters
from items.models import Item


@api_login_required
@require_POST
def toggle_item_bookmark(request, item_id):
    item = get_object_or_404(Item.objects_for_user(request.user), id=item_id)

    deleted, _ = Bookmark.objects.filter(user=request.user, item=item).delete()
    if deleted:
        counters.item_unbookmarked(item)
    else:
        try:
            Bookmark.objects.create(user=request.user, item=item)
        except IntegrityError:
            pass
        else:
            counters.item_bookmarked(item)

    return JsonResponse({"bookmark_count": item.bookmark_count -1 if deleted else item.bookmark_count + 1})
