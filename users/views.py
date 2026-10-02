from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from comments.models import Comment, CommentVote
from common.pagination import paginate
from common.users import get_user_or_404
from items.models import Item, ItemVote
from users.forms import ProfileForm


@login_required
def profile_page(request, slug):
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
