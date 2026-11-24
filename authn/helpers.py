import logging

from functools import wraps

from django.conf import settings
from django.contrib.auth import login

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django_q.tasks import async_task

from notifications.telegram.common import telegram_api
from items.models import Item

log = logging.getLogger(__name__)


def api_login_required(view):
    """Session auth for JSON endpoints. Returns 401 instead of redirecting to the login page."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Нужно войти"}, status=401)
        if request.user.is_banned:
            return JsonResponse({"error": "Аккаунт заблокирован"}, status=403)
        return view(request, *args, **kwargs)

    return wrapper


def start_session(request, user, *, new_user=False):
    if user.deleted_at or user.is_banned:
        return render(request, "error.html", {
            "title": "Вам сюда нельзя", "message": "Аккаунт заблокирован",
        }, status=403)
        
    next_item_id = request.session.get("next_item_id")
    login_message = request.session.get("telegram_login_message")
    login(request, user)
    request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    user.last_activity_at = timezone.now()
    user.save(update_fields=["last_activity_at", "metadata"])
    request.session.pop("telegram_login_message", None)
    if login_message:
        try:
            async_task(telegram_api, "deleteMessage", login_message)
        except Exception:
            log.exception("Could not queue Telegram login prompt cleanup")
    if not user.get_metadata_value("is_onboarded"):
        if next_item_id:
            request.session["next_item_id"] = next_item_id
        return redirect("welcome")
    request.session.pop("next_item_id", None)
    if next_item_id:
        item = Item.objects.filter(id=next_item_id).first()
        if item:
            return redirect(item.get_absolute_url())
    return redirect("user_profile", slug=user.slug)
