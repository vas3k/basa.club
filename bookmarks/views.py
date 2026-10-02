from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from bookmarks.models import Bookmark
from common import counters
from common.pagination import paginate
from items.models import Item, ItemVote


@login_required
def bookmarks_page(request):
    bookmarks = paginate(
        request,
        Bookmark.objects.filter(user=request.user, item__deleted_at__isnull=True)
        .select_related(
            "item",
            "item__category",
            "item__subcategory",
            "item__country",
            "item__city",
            "item__author",
        )
        .order_by("-created_at"),
    )
    items = [bookmark.item for bookmark in bookmarks]
    return render(request, "bookmarks/index.html", {
        "bookmarks": bookmarks,
        "voted_items": ItemVote.voted_item_ids(request.user, items),
    })


@login_required
@require_POST
def remove_bookmark(request, item_id):
    deleted, _ = Bookmark.objects.filter(user=request.user, item_id=item_id).delete()
    if deleted:
        item = Item.objects.filter(pk=item_id).first()
        if item:
            counters.item_unbookmarked(item)

    next_url = request.POST.get("next") or ""
    if next_url != "/bookmarks" and not next_url.startswith("/bookmarks?") and not next_url.startswith("/bookmarks/"):
        next_url = reverse("bookmarks")
    return redirect(next_url)
