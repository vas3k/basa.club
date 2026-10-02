from uuid import uuid4

from django.db import models
from django.db.models import Q
from django.utils import timezone

from common.contacts import present_contacts
from common.models import SoftDeleteMixin
from users.models import User


class Item(SoftDeleteMixin, models.Model):
    VISIBILITY_DRAFT = "draft"
    VISIBILITY_VISIBLE = "visible"
    VISIBILITY_LINK_ONLY = "link_only"
    VISIBILITY = (
        (VISIBILITY_DRAFT, VISIBILITY_DRAFT),
        (VISIBILITY_VISIBLE, VISIBILITY_VISIBLE),
        (VISIBILITY_LINK_ONLY, VISIBILITY_LINK_ONLY),
    )

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    location = models.CharField(max_length=4000, blank=True, default="")
    contacts = models.JSONField(blank=True, default=list)
    promo_code = models.CharField(max_length=32, blank=True, default="")
    images = models.JSONField(blank=True, default=list)
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
    visibility = models.CharField(
        max_length=16,
        choices=VISIBILITY,
        default=VISIBILITY_VISIBLE,
        db_index=True,
    )
    upvotes = models.IntegerField(default=0)
    rating = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    bookmark_count = models.IntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "items"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @classmethod
    def visible_objects(cls):
        now = timezone.now()
        return cls.objects.select_related(
            "category", "subcategory", "country", "city", "author",
        ).filter(
            visibility=cls.VISIBILITY_VISIBLE,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now),
        )

    @classmethod
    def for_author(cls, author):
        return cls.objects.select_related(
            "category", "subcategory", "country", "city", "author",
        ).filter(author=author)

    @classmethod
    def fetch(cls, **lookup):
        return cls.objects.select_related(
            "category", "subcategory", "country", "city", "author",
        ).get(**lookup)

    def get_absolute_url(self):
        country = self.country_id or "everywhere"
        city = self.city_id or "everywhere"
        if not self.subcategory_id:
            return f"/{country}/{city}/{self.category_id}/{self.id}/"
        return f"/{country}/{city}/{self.category_id}/{self.subcategory_id}/{self.id}/"

    @property
    def contact_links(self):
        return present_contacts(self.contacts)

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())

    @property
    def is_listed(self):
        return self.visibility == self.VISIBILITY_VISIBLE and not self.is_expired


class ItemVote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, related_name="item_votes", null=True, on_delete=models.SET_NULL)
    item = models.ForeignKey(Item, related_name="votes", on_delete=models.CASCADE)
    ipaddress = models.GenericIPAddressField(null=True)
    useragent = models.CharField(max_length=512, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "item_votes"
        unique_together = [["user", "item"]]

    @classmethod
    def voted_item_ids(cls, user, items):
        if not user.is_authenticated:
            return set()
        return set(cls.objects.filter(user=user, item__in=items).values_list("item_id", flat=True))
