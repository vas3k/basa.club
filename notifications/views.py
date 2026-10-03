from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from notifications.models import Subscription
from notifications.subscriptions import InvalidSubscription, toggle_subscription


@login_required
@require_POST
def toggle_listing_subscription(request):
    try:
        toggle_subscription(
            request.user,
            request.POST.get("country"),
            request.POST.get("city"),
            request.POST.get("category"),
            request.POST.get("query"),
        )
    except InvalidSubscription:
        pass
    return redirect(_next_url(request))


@login_required
@require_POST
def remove_subscription(request, subscription_id):
    Subscription.objects.filter(user=request.user, pk=subscription_id).delete()
    return redirect(_bookmarks_next(request))


def _bookmarks_next(request):
    target = request.POST.get("next") or ""
    if target == "/bookmarks" or target.startswith("/bookmarks?") or target.startswith("/bookmarks/"):
        return target
    return reverse("bookmarks")


def _next_url(request):
    target = request.POST.get("next") or reverse("index")
    if url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return target
    return reverse("index")
