from django.db import transaction
from django.db.models import F

from comments.models import Comment
from counters.categories import invalidate as invalidate_category
from counters.models import Rating
from geo.models import GeoCity, GeoCountry
from items.models import Item
from users.models import User

VIBE_POINTS = 5
VIBE_SIGNS = {
    Comment.VIBE_GOOD: 1,
    Comment.VIBE_BAD: -1,
}


def vibe_sign(vibe):
    return VIBE_SIGNS.get(vibe, 0)


def item_created(item):
    bump_geo(item, +1)
    bump_user(item.author_id, +1)
    invalidate_category(item.category_id)


def item_updated(item, old):
    bump_geo(old, -1)
    bump_user(old.author_id, -1)
    bump_geo(item, +1)
    bump_user(item.author_id, +1)
    invalidate_category(old.category_id)
    if item.category_id != old.category_id:
        invalidate_category(item.category_id)


def item_hidden(item):
    bump_geo(item, -1)
    bump_user(item.author_id, -1)
    invalidate_category(item.category_id)


@transaction.atomic
def item_upvoted(item):
    Item.objects.filter(pk=item.pk).update(upvotes=F("upvotes") + 1, rating=F("rating") + 1)
    bump_user_upvotes(item.author_id, +1)
    bump_user_rating(item.author_id, +1, f"Плюс за «{_item_title(item)}»")


@transaction.atomic
def item_unvoted(item):
    Item.objects.filter(pk=item.pk).update(upvotes=F("upvotes") - 1, rating=F("rating") - 1)
    bump_user_upvotes(item.author_id, -1)
    bump_user_rating(item.author_id, -1, f"Убрали плюс «{_item_title(item)}»")


def item_bookmarked(item):
    Item.objects.filter(pk=item.pk).update(bookmark_count=F("bookmark_count") + 1)


def item_unbookmarked(item):
    Item.objects.filter(pk=item.pk, bookmark_count__gt=0).update(bookmark_count=F("bookmark_count") - 1)


def comment_created(comment):
    if not comment.reply_to_id:
        Item.objects.filter(pk=comment.item_id).update(comment_count=F("comment_count") + 1)
    bump_user_comments(comment.author_id, +1)
    if not comment.is_on_own_item:
        bump_vibe(comment, +1)


def comment_deleted(comment):
    if not comment.reply_to_id:
        Item.objects.filter(pk=comment.item_id).update(comment_count=F("comment_count") - 1)
        for author_id in Comment.all_objects.filter(
            reply_to=comment,
            deleted_at=comment.deleted_at,
        ).values_list("author_id", flat=True):
            bump_user_comments(author_id, -1)
    bump_user_comments(comment.author_id, -1)


@transaction.atomic
def comment_upvoted(comment):
    updates = {"upvotes": F("upvotes") + 1}
    if not comment.is_on_own_item:
        updates["rating"] = F("rating") + 1
    Comment.objects.filter(pk=comment.pk).update(**updates)
    if comment.is_on_own_item:
        return
    bump_user_upvotes(comment.author_id, +1)
    bump_user_rating(comment.author_id, +1, f"Плюс за комментарий к «{_item_title(comment.item)}»")
    sign = vibe_sign(comment.vibe)
    if sign:
        Item.objects.filter(pk=comment.item_id).update(rating=F("rating") + sign)


@transaction.atomic
def comment_unvoted(comment):
    updates = {"upvotes": F("upvotes") - 1}
    if not comment.is_on_own_item:
        updates["rating"] = F("rating") - 1
    Comment.objects.filter(pk=comment.pk).update(**updates)
    if comment.is_on_own_item:
        return
    bump_user_upvotes(comment.author_id, -1)
    bump_user_rating(comment.author_id, -1, f"Убрали плюс с комментария к «{_item_title(comment.item)}»")
    sign = vibe_sign(comment.vibe)
    if sign:
        Item.objects.filter(pk=comment.item_id).update(rating=F("rating") - sign)


def bump_geo(item, delta):
    """+/- items_count on the country and city this item is listed in.

    Worldwide items (no country) are ignored.
    An item with a country but no city is counted in every city of that country.
    """
    if not item.country_id:
        return

    GeoCountry.objects.filter(pk=item.country_id).update(items_count=F("items_count") + delta)
    if item.city_id:
        GeoCity.objects.filter(pk=item.city_id).update(items_count=F("items_count") + delta)
    else:
        GeoCity.objects.filter(country_id=item.country_id).update(items_count=F("items_count") + delta)


def bump_vibe(comment, delta):
    points = delta * vibe_sign(comment.vibe) * VIBE_POINTS
    if not points:
        return
    reason = _vibe_reason(comment)
    if delta < 0:
        reason = f"Отмена: {reason}"
    bump_user_rating(comment.author_id, points, reason)
    Item.objects.filter(pk=comment.item_id).update(rating=F("rating") + points)


def bump_user_rating(user_id, delta, reason):
    if user_id and delta:
        User.objects.filter(pk=user_id).update(rating=F("rating") + delta)
        Rating.objects.create(user_id=user_id, change=delta, reason=reason)


def bump_user_upvotes(user_id, delta):
    if user_id and delta:
        User.objects.filter(pk=user_id).update(upvotes=F("upvotes") + delta)


def bump_user(user_id, delta):
    if user_id and delta:
        User.objects.filter(pk=user_id).update(items_count=F("items_count") + delta)


def bump_user_comments(user_id, delta):
    if user_id and delta:
        User.objects.filter(pk=user_id).update(comments_count=F("comments_count") + delta)


def _item_title(item):
    return (getattr(item, "title", None) or "объявление").strip()


def _vibe_reason(comment):
    labels = {
        Comment.VIBE_GOOD: "пробовал, доволен",
        Comment.VIBE_BAD: "пробовал, не доволен",
    }
    vibe = labels.get(comment.vibe, "отзыв")
    return f"Отзыв «{vibe}» к «{_item_title(comment.item)}»"
