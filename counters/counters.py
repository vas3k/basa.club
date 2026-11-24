from django.db import transaction
from django.db.models import F

from comments.models import Comment, CommentVote
from counters.categories import invalidate as invalidate_category
from counters.defaults import COMMENT_UPVOTE, ITEM_UPVOTE, VIBE_BAD, VIBE_GOOD
from counters.models import Rating
from geo.models import GeoCity, GeoCountry
from items.models import Item, ItemVote
from users.models import User


def item_created(item):
    bump_geo(item, +1)

    if item.author_id:
        User.objects.filter(id=item.author_id).update(items_count=F("items_count") + 1)

    invalidate_category(item.category_id)


def item_updated(item, old):
    bump_geo(old, -1)
    if old.author_id:
        User.objects.filter(id=old.author_id).update(items_count=F("items_count") - 1)

    bump_geo(item, +1)
    if item.author_id:
        User.objects.filter(id=item.author_id).update(items_count=F("items_count") + 1)

    invalidate_category(old.category_id)
    if item.category_id != old.category_id:
        invalidate_category(item.category_id)


def item_hidden(item):
    bump_geo(item, -1)
    if item.author_id:
        User.objects.filter(id=item.author_id).update(items_count=F("items_count") - 1)

    invalidate_category(item.category_id)


@transaction.atomic
def item_deleted(item, by):
    if not by or not by.is_moderator or by.id == item.author_id:
        return

    upvotes = ItemVote.objects.filter(item=item).exclude(user_id=item.author_id).count()
    author_change = -upvotes * ITEM_UPVOTE
    title = (item.title or "пост").strip()
    weights = {Comment.VIBE_GOOD: VIBE_GOOD, Comment.VIBE_BAD: -VIBE_BAD}
    for comment in Comment.rating_objects().filter(item=item).exclude(author_id=item.author_id):
        author_change -= weights.get(comment.vibe, 0)
        if comment.author_id and comment.rating:
            User.objects.filter(id=comment.author_id).update(
                rating=F("rating") - comment.rating,
                upvotes=F("upvotes") - comment.rating // COMMENT_UPVOTE,
            )
            Rating.objects.create(
                user_id=comment.author_id,
                change=-comment.rating,
                reason=f"Модератор удалил пост с комментарием: «{title}»",
            )

    if item.author_id:
        User.objects.filter(id=item.author_id).update(
            rating=F("rating") + author_change,
            upvotes=F("upvotes") - upvotes,
        )
        if author_change:
            Rating.objects.create(
                user_id=item.author_id,
                change=author_change,
                reason=f"Модератор удалил пост: «{title}»",
            )
    Item.all_objects.filter(id=item.id).update(rating=0)
    Comment.all_objects.filter(item=item).update(rating=0)


@transaction.atomic
def item_upvoted(item):
    Item.objects.filter(id=item.id).update(upvotes=F("upvotes") + 1, rating=F("rating") + ITEM_UPVOTE)
    if item.author_id:
        User.objects.filter(id=item.author_id).update(upvotes=F("upvotes") + 1, rating=F("rating") + ITEM_UPVOTE)
        title = (item.title or "пост").strip()
        Rating.objects.create(user_id=item.author_id, change=ITEM_UPVOTE, reason=f"Плюс за «{title}»")


@transaction.atomic
def item_unvoted(item):
    Item.objects.filter(id=item.id).update(upvotes=F("upvotes") - 1, rating=F("rating") - ITEM_UPVOTE)
    if item.author_id:
        User.objects.filter(id=item.author_id).update(upvotes=F("upvotes") - 1, rating=F("rating") - ITEM_UPVOTE)
        title = (item.title or "пост").strip()
        Rating.objects.create(user_id=item.author_id, change=-ITEM_UPVOTE, reason=f"Убрали плюс «{title}»")


def item_bookmarked(item):
    Item.objects.filter(id=item.id).update(bookmark_count=F("bookmark_count") + 1)


def item_unbookmarked(item):
    Item.objects.filter(id=item.id, bookmark_count__gt=0).update(bookmark_count=F("bookmark_count") - 1)


def comment_created(comment):
    if not comment.reply_to_id:
        Item.objects.filter(id=comment.item_id).update(comment_count=F("comment_count") + 1)
    if comment.author_id:
        User.objects.filter(id=comment.author_id).update(comments_count=F("comments_count") + 1)

    if comment.is_on_own_item:
        return

    title = (comment.item.title or "пост").strip()
    if comment.vibe == Comment.VIBE_GOOD:
        if comment.item.author_id:
            User.objects.filter(id=comment.item.author_id).update(rating=F("rating") + VIBE_GOOD)
            Rating.objects.create(user_id=comment.item.author_id, change=VIBE_GOOD, reason=f"Положительный отзыв к «{title}»")
        Item.objects.filter(id=comment.item_id).update(rating=F("rating") + VIBE_GOOD)
    elif comment.vibe == Comment.VIBE_BAD:
        if comment.item.author_id:
            User.objects.filter(id=comment.item.author_id).update(rating=F("rating") - VIBE_BAD)
            Rating.objects.create(user_id=comment.item.author_id, change=-VIBE_BAD, reason=f"Отрицательный отзыв к «{title}»")
        Item.objects.filter(id=comment.item_id).update(rating=F("rating") - VIBE_BAD)


@transaction.atomic
def comment_updated(comment, old_vibe):
    if comment.vibe == old_vibe or comment.is_on_own_item or comment.reply_to_id:
        return

    weights = {Comment.VIBE_GOOD: VIBE_GOOD, Comment.VIBE_BAD: -VIBE_BAD}
    change = weights.get(comment.vibe, 0) - weights.get(old_vibe, 0)
    if comment.item.author_id and change:
        User.objects.filter(id=comment.item.author_id).update(rating=F("rating") + change)
        title = (comment.item.title or "пост").strip()
        Rating.objects.create(
            user_id=comment.item.author_id,
            change=change,
            reason=f"Изменили оценку отзыва к «{title}»",
        )

    votes = CommentVote.objects.filter(comment_id=comment.id)
    if comment.author_id:
        votes = votes.exclude(user_id=comment.author_id)
    if comment.item.author_id:
        votes = votes.exclude(user_id=comment.item.author_id)
    directions = {Comment.VIBE_GOOD: 1, Comment.VIBE_BAD: -1}
    change += votes.count() * COMMENT_UPVOTE * (directions.get(comment.vibe, 0) - directions.get(old_vibe, 0))
    if change:
        Item.objects.filter(id=comment.item_id).update(rating=F("rating") + change)


@transaction.atomic
def comment_deleted(comment):
    moderator_deleted = bool(comment.deleted_by_id and comment.deleted_by_id != comment.author_id)
    if not comment.reply_to_id:
        Item.objects.filter(id=comment.item_id).update(comment_count=F("comment_count") - 1)
        replies = Comment.all_objects.filter(
            reply_to=comment,
            deleted_at=comment.deleted_at,
        ).select_related("item")
        for reply in replies:
            if reply.author_id:
                User.objects.filter(id=reply.author_id).update(comments_count=F("comments_count") - 1)
            if moderator_deleted:
                decline_comment_rating(reply)

    if comment.author_id:
        User.objects.filter(id=comment.author_id).update(comments_count=F("comments_count") - 1)
    if moderator_deleted:
        decline_comment_rating(comment)


def decline_comment_rating(comment):
    if comment.item.deleted_at and comment.item.deleted_by_id != comment.item.author_id:
        return

    title = (comment.item.title or "пост").strip()
    own_item = bool(comment.author_id and comment.author_id == comment.item.author_id)
    if own_item:
        return

    if comment.vibe == Comment.VIBE_GOOD:
        if comment.item.author_id:
            User.objects.filter(id=comment.item.author_id).update(rating=F("rating") - VIBE_GOOD)
            Rating.objects.create(
                user_id=comment.item.author_id,
                change=-VIBE_GOOD,
                reason=f"Удалили отзыв к «{title}»",
            )
        Item.objects.filter(id=comment.item_id).update(rating=F("rating") - VIBE_GOOD)
    elif comment.vibe == Comment.VIBE_BAD:
        if comment.item.author_id:
            User.objects.filter(id=comment.item.author_id).update(rating=F("rating") + VIBE_BAD)
            Rating.objects.create(
                user_id=comment.item.author_id,
                change=VIBE_BAD,
                reason=f"Удалили отзыв к «{title}»",
            )
        Item.objects.filter(id=comment.item_id).update(rating=F("rating") + VIBE_BAD)

    lost = comment.rating
    if not lost:
        return

    Comment.all_objects.filter(id=comment.id).update(rating=0)
    if comment.vibe == Comment.VIBE_GOOD:
        Item.objects.filter(id=comment.item_id).update(rating=F("rating") - lost)
    elif comment.vibe == Comment.VIBE_BAD:
        Item.objects.filter(id=comment.item_id).update(rating=F("rating") + lost)
    if comment.author_id:
        User.objects.filter(id=comment.author_id).update(
            upvotes=F("upvotes") - lost // COMMENT_UPVOTE,
            rating=F("rating") - lost,
        )
        Rating.objects.create(
            user_id=comment.author_id,
            change=-lost,
            reason=f"Удалили комментарий к «{title}»",
        )


@transaction.atomic
def comment_upvoted(comment):
    updates = {"upvotes": F("upvotes") + 1}
    if not comment.is_on_own_item:
        updates["rating"] = F("rating") + COMMENT_UPVOTE
    Comment.objects.filter(id=comment.id).update(**updates)
    if comment.is_on_own_item:
        return

    if comment.author_id:
        User.objects.filter(id=comment.author_id).update(upvotes=F("upvotes") + 1, rating=F("rating") + COMMENT_UPVOTE)
        title = (comment.item.title or "пост").strip()
        Rating.objects.create(user_id=comment.author_id, change=COMMENT_UPVOTE, reason=f"Плюс за комментарий к «{title}»")

    if comment.vibe == Comment.VIBE_GOOD:
        Item.objects.filter(id=comment.item_id).update(rating=F("rating") + COMMENT_UPVOTE)
    elif comment.vibe == Comment.VIBE_BAD:
        Item.objects.filter(id=comment.item_id).update(rating=F("rating") - COMMENT_UPVOTE)


@transaction.atomic
def comment_unvoted(comment):
    updates = {"upvotes": F("upvotes") - 1}
    if not comment.is_on_own_item:
        updates["rating"] = F("rating") - COMMENT_UPVOTE
    Comment.objects.filter(id=comment.id).update(**updates)
    if comment.is_on_own_item:
        return

    if comment.author_id:
        User.objects.filter(id=comment.author_id).update(upvotes=F("upvotes") - 1, rating=F("rating") - COMMENT_UPVOTE)
        title = (comment.item.title or "пост").strip()
        Rating.objects.create(user_id=comment.author_id, change=-COMMENT_UPVOTE, reason=f"Убрали плюс с комментария к «{title}»")

    if comment.vibe == Comment.VIBE_GOOD:
        Item.objects.filter(id=comment.item_id).update(rating=F("rating") - COMMENT_UPVOTE)
    elif comment.vibe == Comment.VIBE_BAD:
        Item.objects.filter(id=comment.item_id).update(rating=F("rating") + COMMENT_UPVOTE)


def bump_geo(item, delta):
    """+/- items_count on the country and city this item is listed in.

    An item with a country but no city is counted on the country only.
    """
    GeoCountry.objects.filter(id=item.country_id).update(items_count=F("items_count") + delta)
    if item.city_id:
        GeoCity.objects.filter(id=item.city_id).update(items_count=F("items_count") + delta)
