from datetime import timedelta

from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone

from users.models import User

PUBLIC_PREFIXES = (
    "/data_policy/",
    "/banned/",
    "/logout/",
    "/static/",
)

WELCOME_PREFIXES = (
    "/welcome/",
    "/about/",
    "/rules/",
    "/api/images/",
    *PUBLIC_PREFIXES,
)


class AuthSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if request.user.is_banned:
                if not request.path.startswith(PUBLIC_PREFIXES):
                    return redirect("banned")

            if (request.user.metadata or {}).get("welcome_completed") is False:
                if not request.path.startswith(WELCOME_PREFIXES):
                    return redirect("welcome")

            now = timezone.now()
            if not request.user.last_activity_at or request.user.last_activity_at < now - timedelta(minutes=5):
                User.objects.filter(pk=request.user.pk).update(last_activity_at=now)
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)

        return self.get_response(request)
