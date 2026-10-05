from django.http import Http404
from django.shortcuts import get_object_or_404

from users.models import User


def get_user_or_404(request, slug):
    if slug == "me":
        if not request.user.is_authenticated:
            raise Http404()
        slug = request.user.slug
    return get_object_or_404(User, slug=slug)
