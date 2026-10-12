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


def item_created(item):
    bump_geo(item, +1)
    if item.author_id:
        User.objects.filter(pk=item.author_id).update(items_count=F("items_count") + 1)

    invalidate_category(item.category_id)


def item_updated(item, old):
    bump_geo(old, -1)
    if old.author_id:
        User.objects.filter(pk=old.author_id).update(items_count=F("items_count") - 1)

    bump_geo(item, +1)
    if item.author_id:
        User.objects.filter(pk=item.author_id).update(items_count=F("items_count") + 1)

    invalidate_category(old.category_id)
    if item.category_id != old.category_id:
        invalidate_category(item.category_id)


def item_hidden(item):
    bump_geo(item, -1)
    if item.author_id:
        User.objects.filter(pk=item.author_id).update(items_count=F("items_count") - 1)

    invalidate_category(item.category_id)


@transaction.atomic
def item_upvoted(item):
    Item.objects.filter(pk=item.pk).update(upvotes=F("upvotes") + 1, rating=F("rating") + 1)
    if item.author_id:
        User.objects.filter(pk=item.author_id).update(upvotes=F("upvotes") + 1)
        User.objects.filter(pk=item.author_id).update(rating=F("rating") + 1)
        title = (item.title or "пост").strip()
        Rating.objects.create(user_id=item.author_id, change=+1, reason=f"Плюс за «{title}»")


@transaction.atomic
def item_unvoted(item):
    Item.objects.filter(pk=item.pk).update(upvotes=F("upvotes") - 1, rating=F("rating") - 1)
    if item.author_id:
        User.objects.filter(pk=item.author_id).update(upvotes=F("upvotes") - 1)
        User.objects.filter(pk=item.author_id).update(rating=F("rating") - 1)
        title = (item.title or "пост").strip()
        Rating.objects.create(user_id=item.author_id, change=-1, reason=f"Убрали плюс «{title}»")


def item_bookmarked(item):
    Item.objects.filter(pk=item.pk).update(bookmark_count=F("bookmark_count") + 1)


def item_unbookmarked(item):
    Item.objects.filter(pk=item.pk, bookmark_count__gt=0).update(bookmark_count=F("bookmark_count") - 1)


def comment_created(comment):
    if not comment.reply_to_id:
        Item.objects.filter(pk=comment.item_id).update(comment_count=F("comment_count") + 1)
    if comment.author_id:
        User.objects.filter(pk=comment.author_id).update(comments_count=F("comments_count") + 1)

    if not comment.is_on_own_item:
        points = VIBE_SIGNS.get(comment.vibe, 0) * VIBE_POINTS
        if points:
            labels = {
                Comment.VIBE_GOOD: "Положительный отзыв",
                Comment.VIBE_BAD: "Отрицательный отзыв",
            }
            vibe = labels.get(comment.vibe, "Комментарий")
            title = (comment.item.title or "пост").strip()
            if comment.author_id:
                User.objects.filter(pk=comment.author_id).update(rating=F("rating") + points)
                Rating.objects.create(user_id=comment.author_id, change=points, reason=f"{vibe} к «{title}»")
            Item.objects.filter(pk=comment.item_id).update(rating=F("rating") + points)


def comment_deleted(comment):
    if not comment.reply_to_id:
        Item.objects.filter(pk=comment.item_id).update(comment_count=F("comment_count") - 1)
        for author_id in Comment.all_objects.filter(
            reply_to=comment,
            deleted_at=comment.deleted_at,
        ).values_list("author_id", flat=True):
            if author_id:
                User.objects.filter(pk=author_id).update(comments_count=F("comments_count") - 1)
    if comment.author_id:
        User.objects.filter(pk=comment.author_id).update(comments_count=F("comments_count") - 1)


@transaction.atomic
def comment_upvoted(comment):
    updates = {"upvotes": F("upvotes") + 1}
    if not comment.is_on_own_item:
        updates["rating"] = F("rating") + 1
    Comment.objects.filter(pk=comment.pk).update(**updates)
    if comment.is_on_own_item:
        return

    if comment.author_id:
        User.objects.filter(pk=comment.author_id).update(upvotes=F("upvotes") + 1)
        User.objects.filter(pk=comment.author_id).update(rating=F("rating") + 1)
        title = (comment.item.title or "пост").strip()
        Rating.objects.create(user_id=comment.author_id, change=+1, reason=f"Плюс за комментарий к «{title}»")

    sign = VIBE_SIGNS.get(comment.vibe, 0)
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

    if comment.author_id:
        User.objects.filter(pk=comment.author_id).update(upvotes=F("upvotes") - 1)
        User.objects.filter(pk=comment.author_id).update(rating=F("rating") - 1)
        title = (comment.item.title or "пост").strip()
        Rating.objects.create(user_id=comment.author_id, change=-1, reason=f"Убрали плюс с комментария к «{title}»")

    sign = VIBE_SIGNS.get(comment.vibe, 0)
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
