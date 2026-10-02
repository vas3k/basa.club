from django.shortcuts import get_object_or_404

from users.models import User


def get_user_or_404(request, slug):
    if slug == "me":
        return request.user
    return get_object_or_404(User, slug=slug)
