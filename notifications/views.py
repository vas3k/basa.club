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
            (request.POST.get("with_global") or "").lower() in {"1", "true", "on", "yes"},
        )
    except InvalidSubscription:
        pass

    target = request.POST.get("next") or reverse("index")
    if not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        target = reverse("index")
    return redirect(target)


@login_required
@require_POST
def remove_subscription(request, subscription_id):
    Subscription.objects.filter(user=request.user, id=subscription_id).delete()

    target = request.POST.get("next") or ""
    if not (target == "/bookmarks" or target.startswith(("/bookmarks?", "/bookmarks/"))):
        target = reverse("bookmarks")
    return redirect(target)
