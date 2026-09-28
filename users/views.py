from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from common.users import get_user_or_404
from items.models import Item
from users.forms import ProfileForm


@login_required
def profile_page(request, slug):
    profile_user = get_user_or_404(request, slug)
    is_owner = request.user.pk == profile_user.pk
    active_items = Item.visible_objects().filter(author=profile_user)
    inactive_items = Item.for_author(profile_user).exclude(pk__in=active_items.values("pk")) if is_owner else []

    return render(request, "users/profile.html", {
        "profile_user": profile_user,
        "is_owner": is_owner,
        "active_items": active_items,
        "inactive_items": inactive_items,
    })


@login_required
@require_http_methods(["GET", "POST"])
def edit_profile(request, slug):
    user = get_user_or_404(request, slug)
    if user.pk != request.user.pk:
        raise Http404()

    form = ProfileForm(request.POST or None, initial={
        "full_name": user.full_name,
        "city": user.city,
        "country": user.country,
        "bio": user.bio,
    })
    if request.method == "POST" and form.is_valid():
        user.full_name = form.cleaned_data["full_name"]
        user.city = form.cleaned_data["city"]
        user.country = form.cleaned_data["country"]
        user.bio = form.cleaned_data["bio"]
        user.save()
        return redirect("user_profile", slug=slug)

    return render(request, "users/edit.html", {
        "form": form,
        "slug": slug,
    })
