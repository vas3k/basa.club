from collections import Counter

from django.db import transaction
from django.db.models import Count, F

from comments.models import Comment, CommentVote
from items.models import Item, ItemVote
from users.models import User

ITEM_VOTE_POINTS = 1
COMMENT_VOTE_POINTS = 1
COMMENT_VIBE_POINTS = 5
COMMENT_VIBE_VOTE_POINTS = 1

VIBE_SIGNS = {
    Comment.VIBE_GOOD: 1,
    Comment.VIBE_BAD: -1,
}


def vibe_sign(vibe):
    return VIBE_SIGNS.get(vibe, 0)


def bump_rating(model, pk, delta):
    if pk and delta:
        model.objects.filter(pk=pk).update(rating=F("rating") + delta)


def bump_user_rating(user_id, delta):
    bump_rating(User, user_id, delta)


def bump_item_rating(item_id, delta):
    bump_rating(Item, item_id, delta)


def bump_comment_rating(comment_id, delta):
    bump_rating(Comment, comment_id, delta)


def apply_item_vote(item, delta):
    points = delta * ITEM_VOTE_POINTS
    bump_item_rating(item.pk, points)
    bump_user_rating(item.author_id, points)
    item.rating += points


def apply_comment_vibe(comment, delta=1):
    points = delta * vibe_sign(comment.vibe) * COMMENT_VIBE_POINTS
    bump_user_rating(comment.author_id, points)
    bump_item_rating(comment.item_id, points)


def apply_comment_vote(comment, delta):
    points = delta * COMMENT_VOTE_POINTS
    bump_user_rating(comment.author_id, points)
    bump_comment_rating(comment.pk, points)
    bump_item_rating(comment.item_id, delta * vibe_sign(comment.vibe) * COMMENT_VIBE_VOTE_POINTS)
    comment.rating += points


def undo_comment(comment):
    apply_comment_vibe(comment, delta=-1)
    votes = comment.votes.count()
    if votes:
        apply_comment_vote(comment, -votes)
