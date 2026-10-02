from uuid import uuid4

from django.db import models

from items.models import Item
from users.models import User


class Bookmark(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, related_name="bookmarks", on_delete=models.CASCADE)
    item = models.ForeignKey(Item, related_name="bookmarks", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "bookmarks"
        ordering = ["-created_at"]
        unique_together = [["user", "item"]]
