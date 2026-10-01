from django.core.management.base import BaseCommand
from django.db.models import Count

from comments.models import Comment, CommentVote
from items.models import Item, ItemVote
from users.models import User

from common.ratings import ITEM_VOTE_POINTS, COMMENT_VIBE_POINTS, COMMENT_VIBE_VOTE_POINTS, COMMENT_VOTE_POINTS, VIBE_SIGNS, vibe_sign
from collections import Counter 


class Command(BaseCommand):
    help = "Recalculate ratings of all users, items and comments from votes and comment vibes"

    def handle(self, *args, **options):
        users, items, comments = Counter(), Counter(), Counter()

        for row in ItemVote.objects.values("item_id", "item__author_id").annotate(n=Count("pk")).order_by():
            points = row["n"] * ITEM_VOTE_POINTS
            items[row["item_id"]] += points
            users[row["item__author_id"]] += points

        vibe_comments = Comment.objects.filter(
            deleted_at__isnull=True,
            vibe__in=list(VIBE_SIGNS),
        ).values("author_id", "item_id", "vibe").annotate(n=Count("pk")).order_by()
        for row in vibe_comments:
            points = row["n"] * vibe_sign(row["vibe"]) * COMMENT_VIBE_POINTS
            users[row["author_id"]] += points
            items[row["item_id"]] += points

        comment_votes = CommentVote.objects.filter(
            comment__deleted_at__isnull=True,
        ).values(
            "comment_id", "comment__author_id", "comment__item_id", "comment__vibe",
        ).annotate(n=Count("pk")).order_by()
        for row in comment_votes:
            points = row["n"] * COMMENT_VOTE_POINTS
            users[row["comment__author_id"]] += points
            comments[row["comment_id"]] += points
            items[row["comment__item_id"]] += row["n"] * vibe_sign(row["comment__vibe"]) * COMMENT_VIBE_VOTE_POINTS

        for model, model_ratings in ((User, users), (Item, items), (Comment, comments)):
            model.objects.exclude(rating=0).update(rating=0)
            objects = [model(pk=pk, rating=rating) for pk, rating in model_ratings.items() if pk and rating]
            if objects:
                model.objects.bulk_update(objects, ["rating"], batch_size=500)


        self.stdout.write(self.style.SUCCESS("Ratings recalculated"))
