from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import Count, F

from bookmarks.models import Bookmark
from comments.models import Comment, CommentVote
from counters import counters
from counters.categories import refresh_all
from geo.models import GeoCity, GeoCountry
from items.models import Item, ItemVote
from users.models import User


class Command(BaseCommand):
    help = (
        "Recalculate live ratings, upvotes and listing counters from votes, comments and items. "
        "Does not read or write the ratings history table."
    )

    def handle(self, *args, **options):
        # Rebuilds User/Item/Comment.rating and listing counters from current votes
        # and vibes. The ratings history table is an append-only log and is left alone.
        users, items, comments = Counter(), Counter(), Counter()
        user_upvotes = Counter()

        for row in ItemVote.objects.filter(item__deleted_at__isnull=True).values("item_id", "item__author_id").annotate(n=Count("pk")).order_by():
            items[row["item_id"]] += row["n"]
            users[row["item__author_id"]] += row["n"]
            if row["item__author_id"]:
                user_upvotes[row["item__author_id"]] += row["n"]

        for row in Comment.objects.filter(
            vibe__in=list(counters.VIBE_SIGNS),
            item__deleted_at__isnull=True,
        ).exclude(
            author_id=F("item__author_id"),
        ).values("author_id", "item_id", "vibe").annotate(n=Count("pk")).order_by():
            points = row["n"] * counters.VIBE_SIGNS.get(row["vibe"], 0) * counters.VIBE_POINTS
            users[row["author_id"]] += points
            items[row["item_id"]] += points

        for row in CommentVote.objects.filter(
            comment__deleted_at__isnull=True,
            comment__item__deleted_at__isnull=True,
        ).exclude(
            comment__author_id=F("comment__item__author_id"),
        ).values(
            "comment_id", "comment__author_id", "comment__item_id", "comment__vibe",
        ).annotate(n=Count("pk")).order_by():
            users[row["comment__author_id"]] += row["n"]
            comments[row["comment_id"]] += row["n"]
            items[row["comment__item_id"]] += row["n"] * counters.VIBE_SIGNS.get(row["comment__vibe"], 0)
            if row["comment__author_id"]:
                user_upvotes[row["comment__author_id"]] += row["n"]

        for model, values in ((User, users), (Item, items), (Comment, comments)):
            model.objects.exclude(rating=0).update(rating=0)
            objects = [model(pk=pk, rating=rating) for pk, rating in values.items() if pk and rating]
            if objects:
                model.objects.bulk_update(objects, ["rating"], batch_size=500)

        item_upvotes = {
            row["item_id"]: row["n"]
            for row in ItemVote.objects.filter(item__deleted_at__isnull=True).values("item_id").annotate(n=Count("pk")).order_by()
        }
        comment_upvotes = {
            row["comment_id"]: row["n"]
            for row in CommentVote.objects.filter(comment__deleted_at__isnull=True)
            .values("comment_id").annotate(n=Count("pk")).order_by()
        }

        Item.objects.exclude(upvotes=0).update(upvotes=0)
        objects = [Item(pk=pk, upvotes=n) for pk, n in item_upvotes.items() if pk and n]
        if objects:
            Item.objects.bulk_update(objects, ["upvotes"], batch_size=500)

        Comment.objects.exclude(upvotes=0).update(upvotes=0)
        objects = [Comment(pk=pk, upvotes=n) for pk, n in comment_upvotes.items() if pk and n]
        if objects:
            Comment.objects.bulk_update(objects, ["upvotes"], batch_size=500)

        User.objects.exclude(upvotes=0).update(upvotes=0)
        objects = [User(pk=pk, upvotes=n) for pk, n in user_upvotes.items() if pk and n]
        if objects:
            User.objects.bulk_update(objects, ["upvotes"], batch_size=500)

        comment_counts = {
            row["item_id"]: row["n"]
            for row in Comment.objects.filter(reply_to__isnull=True)
            .values("item_id").annotate(n=Count("pk")).order_by()
        }
        Item.objects.exclude(comment_count=0).update(comment_count=0)
        objects = [Item(pk=pk, comment_count=n) for pk, n in comment_counts.items() if pk and n]
        if objects:
            Item.objects.bulk_update(objects, ["comment_count"], batch_size=500)

        bookmark_counts = {
            row["item_id"]: row["n"]
            for row in Bookmark.objects.values("item_id").annotate(n=Count("pk")).order_by()
        }
        Item.objects.exclude(bookmark_count=0).update(bookmark_count=0)
        objects = [Item(pk=pk, bookmark_count=n) for pk, n in bookmark_counts.items() if pk and n]
        if objects:
            Item.objects.bulk_update(objects, ["bookmark_count"], batch_size=500)

        user_items = {
            row["author_id"]: row["n"]
            for row in Item.visible_objects().order_by().values("author_id").annotate(n=Count("pk"))
        }
        user_comments = {
            row["author_id"]: row["n"]
            for row in Comment.objects.filter(author_id__isnull=False)
            .values("author_id").annotate(n=Count("pk")).order_by()
        }
        User.objects.exclude(items_count=0, comments_count=0).update(items_count=0, comments_count=0)
        objects = []
        for user in User.objects.all().only("pk"):
            items_count = user_items.get(user.pk, 0)
            comments_count = user_comments.get(user.pk, 0)
            if items_count or comments_count:
                objects.append(User(pk=user.pk, items_count=items_count, comments_count=comments_count))
        if objects:
            User.objects.bulk_update(objects, ["items_count", "comments_count"], batch_size=500)

        visible = Item.visible_objects().order_by()
        worldwide = visible.filter(country__isnull=True).count()
        country_counts = {
            row["country_id"]: row["n"]
            for row in visible.exclude(country__isnull=True).values("country_id").annotate(n=Count("pk"))
        }
        countries = list(GeoCountry.objects.all())
        for country in countries:
            country.items_count = country_counts.get(country.id, 0)
        if countries:
            GeoCountry.objects.bulk_update(countries, ["items_count"])

        city_counts = {
            row["city_id"]: row["n"]
            for row in visible.exclude(city__isnull=True).values("city_id").annotate(n=Count("pk"))
        }
        cities = list(GeoCity.objects.all())
        for city in cities:
            city.items_count = city_counts.get(city.id, 0)
        if cities:
            GeoCity.objects.bulk_update(cities, ["items_count"])

        category_totals = refresh_all()
        self.stdout.write("Categories: " + ", ".join(f"{root_id} {total}" for root_id, total in category_totals.items()))
        self.stdout.write(f"Geo: {worldwide} worldwide ignored, {len(countries)} countries, {len(cities)} cities")
        self.stdout.write(self.style.SUCCESS("Live ratings and counters recalculated"))
