from datetime import timedelta

from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone

from users.models import User


class AuthSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.is_banned:
            return redirect("banned")

        if request.user.is_authenticated:
            now = timezone.now()
            if not request.user.last_activity_at or request.user.last_activity_at < now - timedelta(minutes=5):
                User.objects.filter(pk=request.user.pk).update(last_activity_at=now)
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)

        return self.get_response(request)
