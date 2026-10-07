from functools import wraps

from django.conf import settings
from django.contrib.auth import login

from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone


def api_login_required(view):
    """Session auth for JSON endpoints. Returns 401 instead of redirecting to the login page."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Нужно войти"}, status=401)
        return view(request, *args, **kwargs)

    return wrapper


def start_session(request, user, *, new_user=False):
    login(request, user)
    if new_user:
        # False sends the user through /welcome/. A missing key is an older account.
        metadata = dict(user.metadata or {})
        metadata["welcome_completed"] = False
        user.metadata = metadata
    request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    user.last_activity_at = timezone.now()
    user.save(update_fields=["last_activity_at", "metadata"])
    return redirect("user_profile", slug=user.slug)
