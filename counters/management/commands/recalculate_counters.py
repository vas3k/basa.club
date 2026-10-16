from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, F

from bookmarks.models import Bookmark
from comments.models import Comment, CommentVote
from counters.categories import refresh_all
from counters.defaults import COMMENT_UPVOTE, ITEM_UPVOTE, VIBE_BAD, VIBE_GOOD
from counters.models import Rating
from geo.models import GeoCity, GeoCountry
from items.models import Item, ItemVote
from users.models import User


class Command(BaseCommand):
    help = (
        "Recalculate live ratings, upvotes and listing counters from votes, comments and items. "
        "Replaces rating history for every recalculated user with current contributing events."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        users, items, comments = Counter(), Counter(), Counter()
        user_upvotes = Counter()
        user_ids = set(User.objects.values_list("id", flat=True))
        history = []

        for row in ItemVote.objects.filter(item__deleted_at__isnull=True).exclude(
            user_id__isnull=False,
            user_id=F("item__author_id"),
        ).values("item_id", "item__author_id", "item__title", "created_at").iterator():
            items[row["item_id"]] += ITEM_UPVOTE
            users[row["item__author_id"]] += ITEM_UPVOTE
            if row["item__author_id"]:
                user_upvotes[row["item__author_id"]] += 1
            if row["item__author_id"] in user_ids:
                title = (row["item__title"] or "пост").strip()
                history.append(Rating(
                    user_id=row["item__author_id"],
                    change=ITEM_UPVOTE,
                    reason=f"Плюс за «{title}»",
                    created_at=row["created_at"],
                ))

        for row in Comment.objects.filter(
            vibe__in=[Comment.VIBE_GOOD, Comment.VIBE_BAD],
            item__deleted_at__isnull=True,
        ).exclude(
            author_id=F("item__author_id"),
        ).values("item__author_id", "item_id", "vibe", "item__title", "created_at").iterator():
            if row["vibe"] == Comment.VIBE_GOOD:
                users[row["item__author_id"]] += VIBE_GOOD
                items[row["item_id"]] += VIBE_GOOD
            elif row["vibe"] == Comment.VIBE_BAD:
                users[row["item__author_id"]] -= VIBE_BAD
                items[row["item_id"]] -= VIBE_BAD
            if row["item__author_id"] in user_ids:
                title = (row["item__title"] or "пост").strip()
                positive = row["vibe"] == Comment.VIBE_GOOD
                history.append(Rating(
                    user_id=row["item__author_id"],
                    change=VIBE_GOOD if positive else -VIBE_BAD,
                    reason=f"Положительный отзыв к «{title}»" if positive else f"Отрицательный отзыв к «{title}»",
                    created_at=row["created_at"],
                ))

        for row in CommentVote.objects.filter(
            comment__deleted_at__isnull=True,
            comment__item__deleted_at__isnull=True,
        ).exclude(
            comment__author_id=F("comment__item__author_id"),
        ).exclude(
            user_id__isnull=False,
            user_id=F("comment__author_id"),
        ).exclude(
            user_id__isnull=False,
            user_id=F("comment__item__author_id"),
        ).values(
            "comment_id", "comment__author_id", "comment__item_id", "comment__vibe",
            "comment__item__title", "created_at",
        ).iterator():
            weight = COMMENT_UPVOTE
            users[row["comment__author_id"]] += weight
            comments[row["comment_id"]] += weight
            if row["comment__vibe"] == Comment.VIBE_GOOD:
                items[row["comment__item_id"]] += weight
            elif row["comment__vibe"] == Comment.VIBE_BAD:
                items[row["comment__item_id"]] -= weight
            if row["comment__author_id"]:
                user_upvotes[row["comment__author_id"]] += 1
            if row["comment__author_id"] in user_ids:
                title = (row["comment__item__title"] or "пост").strip()
                history.append(Rating(
                    user_id=row["comment__author_id"],
                    change=COMMENT_UPVOTE,
                    reason=f"Плюс за комментарий к «{title}»",
                    created_at=row["created_at"],
                ))

        for model, values in ((User, users), (Item, items), (Comment, comments)):
            model.objects.exclude(rating=0).update(rating=0)
            objects = [model(id=pk, rating=rating) for pk, rating in values.items() if pk and rating]
            if objects:
                model.objects.bulk_update(objects, ["rating"], batch_size=500)

        Rating.objects.filter(user_id__in=user_ids).delete()
        if history:
            # auto_now_add overwrites supplied timestamps during bulk_create.
            timestamps = [entry.created_at for entry in history]
            Rating.objects.bulk_create(history, batch_size=500)
            for entry, created_at in zip(history, timestamps):
                entry.created_at = created_at
            Rating.objects.bulk_update(history, ["created_at"], batch_size=500)

        item_upvotes = {
            row["item_id"]: row["n"]
            for row in ItemVote.objects.filter(item__deleted_at__isnull=True).values("item_id").annotate(n=Count("id")).order_by()
        }
        comment_upvotes = {
            row["comment_id"]: row["n"]
            for row in CommentVote.objects.filter(comment__deleted_at__isnull=True)
            .values("comment_id").annotate(n=Count("id")).order_by()
        }

        Item.objects.exclude(upvotes=0).update(upvotes=0)
        objects = [Item(id=pk, upvotes=n) for pk, n in item_upvotes.items() if pk and n]
        if objects:
            Item.objects.bulk_update(objects, ["upvotes"], batch_size=500)

        Comment.objects.exclude(upvotes=0).update(upvotes=0)
        objects = [Comment(id=pk, upvotes=n) for pk, n in comment_upvotes.items() if pk and n]
        if objects:
            Comment.objects.bulk_update(objects, ["upvotes"], batch_size=500)

        User.objects.exclude(upvotes=0).update(upvotes=0)
        objects = [User(id=pk, upvotes=n) for pk, n in user_upvotes.items() if pk and n]
        if objects:
            User.objects.bulk_update(objects, ["upvotes"], batch_size=500)

        comment_counts = {
            row["item_id"]: row["n"]
            for row in Comment.objects.filter(reply_to__isnull=True)
            .values("item_id").annotate(n=Count("id")).order_by()
        }
        Item.objects.exclude(comment_count=0).update(comment_count=0)
        objects = [Item(id=pk, comment_count=n) for pk, n in comment_counts.items() if pk and n]
        if objects:
            Item.objects.bulk_update(objects, ["comment_count"], batch_size=500)

        bookmark_counts = {
            row["item_id"]: row["n"]
            for row in Bookmark.objects.values("item_id").annotate(n=Count("id")).order_by()
        }
        Item.objects.exclude(bookmark_count=0).update(bookmark_count=0)
        objects = [Item(id=pk, bookmark_count=n) for pk, n in bookmark_counts.items() if pk and n]
        if objects:
            Item.objects.bulk_update(objects, ["bookmark_count"], batch_size=500)

        user_items = {
            row["author_id"]: row["n"]
            for row in Item.visible_objects().order_by().values("author_id").annotate(n=Count("id"))
        }
        user_comments = {
            row["author_id"]: row["n"]
            for row in Comment.objects.filter(author_id__isnull=False)
            .values("author_id").annotate(n=Count("id")).order_by()
        }
        User.objects.exclude(items_count=0, comments_count=0).update(items_count=0, comments_count=0)
        objects = []
        for user in User.objects.all().only("id"):
            items_count = user_items.get(user.id, 0)
            comments_count = user_comments.get(user.id, 0)
            if items_count or comments_count:
                objects.append(User(id=user.id, items_count=items_count, comments_count=comments_count))
        if objects:
            User.objects.bulk_update(objects, ["items_count", "comments_count"], batch_size=500)

        visible = Item.visible_objects().order_by()
        country_counts = {
            row["country_id"]: row["n"]
            for row in visible.values("country_id").annotate(n=Count("id"))
        }
        countries = list(GeoCountry.objects.all())
        for country in countries:
            country.items_count = country_counts.get(country.id, 0)
        if countries:
            GeoCountry.objects.bulk_update(countries, ["items_count"])

        city_counts = {
            row["city_id"]: row["n"]
            for row in visible.exclude(city__isnull=True).values("city_id").annotate(n=Count("id"))
        }
        cities = list(GeoCity.objects.all())
        for city in cities:
            city.items_count = city_counts.get(city.id, 0)
        if cities:
            GeoCity.objects.bulk_update(cities, ["items_count"])

        category_totals = refresh_all()
        self.stdout.write("Categories: " + ", ".join(f"{root_id} {total}" for root_id, total in category_totals.items()))
        self.stdout.write(f"Geo: {len(countries)} countries, {len(cities)} cities")
        self.stdout.write(self.style.SUCCESS("Live ratings, counters and rating history rebuilt"))
