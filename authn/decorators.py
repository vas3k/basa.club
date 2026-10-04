from functools import wraps

from django.http import JsonResponse


def api_login_required(view):
    """Session auth for JSON endpoints. Returns 401 instead of redirecting to the login page."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Нужно войти"}, status=401)
        return view(request, *args, **kwargs)

    return wrapper
