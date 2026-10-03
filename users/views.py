from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from comments.models import Comment, CommentVote
from common.pagination import paginate
from common.users import get_user_or_404
from geo.models import GeoCity, GeoCountry
from items.models import Item, ItemVote
from users.forms import EVERYWHERE, ProfileForm, WelcomeForm
from notifications.subscriptions import subscribe_to_geo


@login_required
def profile_page(request, slug):
    if (request.user.metadata or {}).get("welcome_completed") is False:
        return redirect("welcome")
    if not request.user.telegram_id:
        return redirect("bot")

    profile_user = get_user_or_404(request, slug)
    is_owner = request.user.pk == profile_user.pk
    active_items = paginate(
        request,
        Item.visible_objects().filter(author=profile_user),
        settings.PROFILE_POSTS_PAGE_SIZE,
    )
    inactive_items = paginate(
        request,
        Item.for_author(profile_user).exclude(pk__in=Item.visible_objects().filter(author=profile_user).values("pk")) if is_owner else Item.objects.none(),
        settings.PROFILE_POSTS_PAGE_SIZE,
        "inactive_page",
    )
    comments = paginate(
        request,
        Comment.visible_objects()
        .filter(author=profile_user, reply_to__isnull=True)
        .select_related("item", "item__city", "item__subcategory")
        .order_by("-created_at"),
        settings.PROFILE_COMMENTS_PAGE_SIZE,
        "comments_page",
    )
    voted_comments = set(
        CommentVote.objects.filter(user=request.user, comment__in=comments.object_list).values_list("comment_id", flat=True)
    )

    return render(request, "users/profile.html", {
        "profile_user": profile_user,
        "is_owner": is_owner,
        "active_items": active_items,
        "inactive_items": inactive_items,
        "comments": comments,
        "voted_comments": voted_comments,
        "voted_items": ItemVote.voted_item_ids(request.user, list(active_items) + list(inactive_items)),
    })


@login_required
@require_http_methods(["GET", "POST"])
def edit_profile(request, slug):
    user = get_user_or_404(request, slug)
    if user.pk != request.user.pk:
        raise Http404()

    form = ProfileForm(request.POST or None, initial={
        "full_name": user.full_name,
        "avatar": user.avatar,
        "city": user.city,
        "country": user.country,
        "bio": user.bio,
    })
    if request.method == "POST" and form.is_valid():
        user.full_name = form.cleaned_data["full_name"]
        user.avatar = form.cleaned_data["avatar"] or None
        user.city = form.cleaned_data["city"]
        user.country = form.cleaned_data["country"]
        user.bio = form.cleaned_data["bio"]
        user.save()
        return redirect("user_profile", slug=slug)

    return render(request, "users/edit.html", {
        "form": form,
        "slug": slug,
    })


@login_required
@require_http_methods(["GET", "POST"])
def welcome(request):
    if (request.user.metadata or {}).get("welcome_completed") is not False:
        return redirect("user_profile", slug="me")

    user = request.user
    country_id, city_id = _geo_selection(user)
    form = WelcomeForm(request.POST or None, instance=user, initial={
        "country": country_id,
        "city": city_id,
    })
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        metadata = dict(user.metadata or {})
        metadata["welcome_completed"] = True
        user.metadata = metadata
        subscribe_to_geo(user, form.cleaned_data["country_id"], form.cleaned_data["city_id"])
        user.save()
        return redirect("user_profile", slug="me")

    country_id = form["country"].value() or ""
    city_id = form["city"].value() or ""

    return render(request, "users/welcome.html", {
        "form": form,
        "country_id": country_id,
        "city_id": city_id,
        "countries_options": _country_options(),
    })


def _country_options():
    return [
        {
            "id": country.id,
            "name": country.name,
            "icon": country.icon,
            "cities": [{"id": city.id, "name": city.name, "icon": city.icon} for city in country.cities.all()],
        }
        for country in GeoCountry.objects.prefetch_related("cities")
    ]


def _geo_selection(user):
    if not user.country:
        return EVERYWHERE, EVERYWHERE
    country = GeoCountry.objects.filter(name=user.country).first()
    if not country:
        return EVERYWHERE, EVERYWHERE
    if not user.city:
        return country.id, EVERYWHERE
    city = GeoCity.objects.filter(country=country, name=user.city).first()
    if not city:
        return country.id, EVERYWHERE
    return country.id, city.id
