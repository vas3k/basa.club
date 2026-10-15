from functools import wraps

from django.conf import settings
from django.contrib.auth import login

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone


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
    if user.is_banned:
        return render(request, "error.html", {
            "title": "Вам сюда нельзя", "message": "Аккаунт заблокирован",
        }, status=403)
        
    login(request, user)
    request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    user.last_activity_at = timezone.now()
    user.save(update_fields=["last_activity_at", "metadata"])
    return redirect("user_profile", slug=user.slug)
