import uuid
from uuid import uuid4

from django.db import models

from users.models import User


class Category(models.Model):
    id = models.CharField(max_length=16, primary_key=True, editable=True)
    name = models.CharField(max_length=255, unique=True)
    icon = models.CharField(max_length=255)
    description = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "categories"
        ordering = ["name"]


class Geo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    geojson = models.JSONField(null=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "geo"
        ordering = ["slug"]


class Item(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    title = models.CharField(max_length=200)
    text = models.TextField(null=True, blank=True)
    html = models.TextField(null=True, blank=True)
    url = models.URLField(max_length=1024, null=True)
    image = models.URLField(max_length=1024, null=True)
    price = models.CharField(max_length=255, null=True, blank=True)
    special_code = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    geo = models.ForeignKey(Geo, on_delete=models.CASCADE)

    rating = models.FloatField(default=0)
    view_count = models.IntegerField(default=0)
    upvote_count = models.IntegerField(default=0)
    downvote_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    expired_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "items"
        ordering = ["-created_at"]
