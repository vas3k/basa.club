from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import BigIntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Extract, Round
from django.utils import timezone

from common.models import SoftDeleteManager, SoftDeleteMixin, SoftDeleteQuerySet
from items.models import Item
from users.models import User


class CommentQuerySet(SoftDeleteQuerySet):
    def delete(self, by=None):
        now = timezone.now()
        pks = list(self.values_list("id", flat=True))
        count = self.model.all_objects.filter(Q(id__in=pks) | Q(reply_to_id__in=pks)).update(
            deleted_at=now,
            deleted_by=by,
        )
        return count, {self.model._meta.label: count}


class CommentManager(SoftDeleteManager):
    def get_queryset(self):
        return CommentQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


class Comment(SoftDeleteMixin, models.Model):
    VIBE_GOOD = "good"
    VIBE_BAD = "bad"
    VIBE_NEUTRAL = "neutral"
    VIBES = (
        (VIBE_GOOD, "👍 Пробовал, доволен"),
        (VIBE_BAD, "👎 Пробовал, не доволен"),
        (VIBE_NEUTRAL, "💬 Нейтрально"),
    )

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    author = models.ForeignKey(User, related_name="comments", null=True, on_delete=models.SET_NULL)
    item = models.ForeignKey(Item, related_name="comments", on_delete=models.CASCADE)
    reply_to = models.ForeignKey("self", related_name="replies", null=True, blank=True, on_delete=models.CASCADE)
    text = models.TextField()
    vibe = models.CharField(max_length=16, choices=VIBES, null=True, blank=True)  # only top-level comments have it
    ipaddress = models.GenericIPAddressField(null=True)
    useragent = models.CharField(max_length=512, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    upvotes = models.IntegerField(default=0)
    rating = models.IntegerField(default=0)

    objects = CommentManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "comments"
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        if self.reply_to_id:
            parent = Comment.objects.filter(id=self.reply_to_id).first()
            if not parent or parent.item_id != self.item_id:
                raise ValidationError("Этот комментарий не существует")

            if parent.reply_to_id:
                raise ValidationError("Отвечать можно только на исходный комментарий")

        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False, by=None):
        super().delete(using=using, keep_parents=keep_parents, by=by)
        if not self.reply_to_id:
            type(self).objects.filter(reply_to=self).update(
                deleted_at=self.deleted_at,
                deleted_by=self.deleted_by,
            )

    @property
    def is_on_own_item(self):
        return bool(self.author_id and self.author_id == self.item.author_id)

    def is_editable(self):
        return timezone.now() < self.created_at + settings.COMMENT_EDIT_PERIOD

    def is_deletable(self):
        return timezone.now() < self.created_at + settings.COMMENT_DELETE_PERIOD

    @classmethod
    def check_rate_limits(cls, user):
        since = timezone.now() - settings.RATE_LIMIT_PERIOD
        recent = cls.all_objects.filter(author=user, created_at__gte=since).count()
        return recent < settings.COMMENT_RATE_LIMIT

    @classmethod
    def visible_objects(cls):
        return cls.objects.select_related("author", "reply_to")

    @classmethod
    def objects_for_user(cls, user, queryset=None):
        queryset = cls.visible_objects() if queryset is None else queryset
        if not user or not user.is_authenticated:
            return queryset

        vote_qs = CommentVote.objects.filter(comment=OuterRef("id"), user=user)
        return queryset.annotate(
            upvoted_at=Subquery(
                vote_qs.annotate(
                    epoch_ms=Round(Extract("created_at", "epoch") * 1000)
                ).values("epoch_ms")[:1],
                output_field=BigIntegerField(),
            ),
        )


class CommentVote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, related_name="comment_votes", null=True, on_delete=models.SET_NULL)
    item = models.ForeignKey(Item, related_name="comment_votes", on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, related_name="votes", on_delete=models.CASCADE)
    ipaddress = models.GenericIPAddressField(null=True)
    useragent = models.CharField(max_length=512, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comment_votes"
        unique_together = [["user", "comment"]]

    def is_retractable(self):
        return timezone.now() < self.created_at + settings.VOTE_RETRACT_PERIOD

    @classmethod
    def check_rate_limits(cls, user):
        since = timezone.now() - settings.RATE_LIMIT_PERIOD
        recent = cls.objects.filter(user=user, created_at__gte=since).count()
        return recent < settings.COMMENT_VOTE_RATE_LIMIT
