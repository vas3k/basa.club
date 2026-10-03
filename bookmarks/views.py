from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from bookmarks.models import Bookmark
from common import counters
from common.pagination import paginate
from items.models import Item
from notifications.models import Subscription


@login_required
def bookmarks_page(request):
    items = paginate(
        request,
        Item.objects_for_user(request.user, Item.objects.select_related(
            "category",
            "subcategory",
            "country",
            "city",
            "author",
        ).filter(bookmarks__user=request.user).order_by("-bookmarks__created_at")),
    )
    subscriptions = (
        Subscription.objects.filter(user=request.user)
        .select_related("country", "city", "category")
        .order_by("-created_at")
    )
    
    return render(request, "bookmarks/index.html", {
        "items": items,
        "subscriptions": subscriptions,
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
