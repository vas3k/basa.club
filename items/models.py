from uuid import uuid4

from django.db import models

from users.models import User


class Item(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.CASCADE,
        related_name="items",
    )
    subcategory = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subcategory_items",
    )
    country = models.ForeignKey(
        "geo.GeoCountry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    city = models.ForeignKey(
        "geo.GeoCity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="items")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "items"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
