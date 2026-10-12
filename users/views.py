from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from comments.models import Comment
from common.pagination import paginate
from common.users import get_user_or_404
from geo.models import GeoCity, GeoCountry
from items.models import Item
from users.forms import EVERYWHERE, ProfileForm, WelcomeForm
from notifications.subscriptions import subscribe_to_geo


@login_required
def profile_page(request, slug):
    if (request.user.metadata or {}).get("welcome_completed") is False:
        return redirect("welcome")

    if not request.user.telegram_id:
        return redirect("bot")

    profile_user = get_user_or_404(request, slug)
    active_items = paginate(
        request,
        Item.objects_for_user(request.user).filter(author=profile_user),
        settings.PROFILE_POSTS_PAGE_SIZE,
    )
    inactive_items = Item.objects.none()
    if request.user.pk == profile_user.pk:
        visible_ids = Item.visible_objects().filter(author=profile_user).values("pk")
        inactive_items = Item.for_author(profile_user).exclude(pk__in=visible_ids)
        inactive_items = Item.objects_for_user(request.user, inactive_items)

    inactive_items = paginate(
        request,
        inactive_items,
        settings.PROFILE_POSTS_PAGE_SIZE,
        "inactive_page",
    )
    comments = paginate(
        request,
        Comment.objects_for_user(request.user)
        .filter(author=profile_user, reply_to__isnull=True)
        .select_related("item", "item__city", "item__subcategory")
        .order_by("-created_at"),
        settings.PROFILE_COMMENTS_PAGE_SIZE,
        "comments_page",
    )

    return render(request, "users/profile.html", {
        "profile_user": profile_user,
        "active_items": active_items,
        "inactive_items": inactive_items,
        "comments": comments,
    })


@login_required
@require_http_methods(["GET", "POST"])
def edit_profile(request, slug):
    user = get_user_or_404(request, slug)
    if user.pk != request.user.pk:
        raise Http404()

    country = GeoCountry.objects.filter(name=user.country).first() if user.country else None
    city = GeoCity.objects.filter(country=country, name=user.city).first() if country and user.city else None
    country_id = country.id if country else EVERYWHERE
    city_id = city.id if city else EVERYWHERE

    form = ProfileForm(request.POST or None, instance=user, initial={
        "country": country_id,
        "city": city_id,
    })
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("user_profile", slug=user.slug)

    countries = [
        {
            "id": country.id,
            "name": country.name,
            "icon": country.icon,
            "cities": [{"id": city.id, "name": city.name, "icon": city.icon} for city in country.cities.all()],
        }
        for country in GeoCountry.objects.prefetch_related("cities")
    ]

    return render(request, "users/edit.html", {
        "form": form,
        "slug": user.slug,
        "country_id": form["country"].value() or "",
        "city_id": form["city"].value() or "",
        "countries_options": countries,
    })


@login_required
@require_http_methods(["GET", "POST"])
def welcome(request):
    if (request.user.metadata or {}).get("welcome_completed") is not False:
        return redirect("user_profile", slug=request.user.slug)

    user = request.user
    country = GeoCountry.objects.filter(name=user.country).first() if user.country else None
    city = GeoCity.objects.filter(country=country, name=user.city).first() if country and user.city else None
    country_id = country.id if country else EVERYWHERE
    city_id = city.id if city else EVERYWHERE

    form = WelcomeForm(request.POST or None, instance=user, initial={
        "country": country_id,
        "city": city_id,
    })

    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        metadata = dict(user.metadata or {})
        metadata["welcome_completed"] = True
        user.metadata = metadata
        user.save()

        subscribe_to_geo(user, form.cleaned_data["country_id"], form.cleaned_data["city_id"])

        return redirect("user_profile", slug=user.slug)

    country_id = form["country"].value() or ""
    city_id = form["city"].value() or ""

    countries = [
        {
            "id": country.id,
            "name": country.name,
            "icon": country.icon,
            "cities": [{"id": city.id, "name": city.name, "icon": city.icon} for city in country.cities.all()],
        }
        for country in GeoCountry.objects.prefetch_related("cities")
    ]

    return render(request, "users/welcome.html", {
        "form": form,
        "country_id": country_id,
        "city_id": city_id,
        "countries_options": countries,
    })
