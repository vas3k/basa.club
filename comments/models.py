from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F

from common.request import parse_ip_address, parse_useragent
from items.models import Item
from users.models import User


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    author = models.ForeignKey(User, related_name="comments", null=True, on_delete=models.SET_NULL)
    item = models.ForeignKey(Item, related_name="comments", on_delete=models.CASCADE)
    reply_to = models.ForeignKey("self", related_name="replies", null=True, blank=True, on_delete=models.CASCADE)
    text = models.TextField()
    ipaddress = models.GenericIPAddressField(null=True)
    useragent = models.CharField(max_length=512, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    upvotes = models.IntegerField(default=0)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "comments"
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        if self.reply_to_id:
            parent = Comment.objects.select_related("reply_to__reply_to").filter(pk=self.reply_to_id).first()
            if not parent or parent.item_id != self.item_id:
                raise ValidationError("Ответ должен быть к комментарию этого объявления")
            if parent.reply_to_id and parent.reply_to and parent.reply_to.reply_to_id:
                raise ValidationError("3 уровня комментариев это максимум")
        super().save(*args, **kwargs)
        self.item.refresh_comment_count()

    def is_deleted(self):
        return self.deleted_at is not None

    def increment_vote_count(self):
        Comment.objects.filter(pk=self.pk).update(upvotes=F("upvotes") + 1)
        self.upvotes += 1

    @classmethod
    def visible_objects(cls):
        return cls.objects.filter(deleted_at__isnull=True).select_related("author", "reply_to")


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

    @classmethod
    def upvote(cls, user, comment, request):
        if comment.author_id and user.pk == comment.author_id:
            return None, False

        vote, created = cls.objects.get_or_create(
            user=user,
            comment=comment,
            defaults={
                "item": comment.item,
                "ipaddress": parse_ip_address(request),
                "useragent": parse_useragent(request),
            },
        )
        if created:
            comment.increment_vote_count()
            if comment.author_id:
                comment.author.increment_vote_count()
        return vote, created
