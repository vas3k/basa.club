from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render

from common.users import get_user_or_404
from counters.models import Rating

RATINGS_LIMIT = 100


@login_required
def user_ratings(request, slug):
    profile_user = get_user_or_404(request, slug)
    if profile_user.id != request.user.id and not request.user.is_moderator:
        raise Http404()

    ratings = list(
        Rating.objects.filter(user=profile_user).order_by("-created_at")[:RATINGS_LIMIT]
    )
    return render(request, "users/ratings.html", {
        "profile_user": profile_user,
        "ratings": ratings,
    })
