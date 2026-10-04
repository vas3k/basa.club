from uuid import uuid4

from django.db import models

from items.models import Item
from users.models import User


class Flag(models.Model):
    REASON_DUPLICATE = "duplicate"
    REASON_SPAM = "spam"
    REASON_SCAMMER = "scammer"
    REASON_OTHER = "other"
    REASONS = (
        (REASON_DUPLICATE, "Дубликат"),
        (REASON_SPAM, "Спамеры"),
        (REASON_SCAMMER, "Мошенники"),
        (REASON_OTHER, "Другое"),
    )
    COMMENT_MAX_LENGTH = 1000

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, related_name="flags", on_delete=models.CASCADE)
    item = models.ForeignKey(Item, related_name="flags", on_delete=models.CASCADE)
    reason = models.CharField(max_length=16, choices=REASONS, verbose_name="Причина")
    comment = models.TextField(blank=True, default="", verbose_name="Комментарий")
    ipaddress = models.GenericIPAddressField(null=True)
    useragent = models.CharField(max_length=512, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "flags"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_reason_display()}: {self.item}"
