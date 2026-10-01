from uuid import uuid4

from django.db import models
from django.db.models import Count, F, Q
from django.utils import timezone

from users.models import User


class Item(models.Model):
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

    @classmethod
    def recalculate_counters(cls):
        from categories.models import Category
        from geo.models import GeoCity, GeoCountry

        visible = cls.visible_objects().order_by()

        category_counts = {
            row["category_id"]: row["n"]
            for row in visible.values("category_id").annotate(n=Count("pk"))
        }
        subcategory_counts = {
            row["subcategory_id"]: row["n"]
            for row in visible.exclude(subcategory__isnull=True).values("subcategory_id").annotate(n=Count("pk"))
        }
        categories = list(Category.objects.all())
        for category in categories:
            if category.parent_id:
                category.items_count = subcategory_counts.get(category.id, 0)
            else:
                category.items_count = category_counts.get(category.id, 0)
        if categories:
            Category.objects.bulk_update(categories, ["items_count"])

        global_items = visible.filter(country__isnull=True).count()
        country_counts = {
            row["country_id"]: row["n"]
            for row in visible.exclude(country__isnull=True).values("country_id").annotate(n=Count("pk"))
        }
        countries = list(GeoCountry.objects.all())
        for country in countries:
            country.items_count = country_counts.get(country.id, 0) + global_items
        if countries:
            GeoCountry.objects.bulk_update(countries, ["items_count"])

        city_counts = {
            row["city_id"]: row["n"]
            for row in visible.exclude(city__isnull=True).values("city_id").annotate(n=Count("pk"))
        }
        countrywide = {
            row["country_id"]: row["n"]
            for row in visible.filter(city__isnull=True, country__isnull=False).values("country_id").annotate(n=Count("pk"))
        }
        cities = list(GeoCity.objects.all())
        for city in cities:
            city.items_count = city_counts.get(city.id, 0) + countrywide.get(city.country_id, 0) + global_items
        if cities:
            GeoCity.objects.bulk_update(cities, ["items_count"])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.recalculate_counters()

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        self.recalculate_counters()
        return result

    def get_absolute_url(self):
        if not self.subcategory_id:
            return ""
        country = self.country_id or "everywhere"
        city = self.city_id or "everywhere"
        return f"/{country}/{city}/{self.category_id}/{self.subcategory_id}/{self.id}/"

    def increment_vote_count(self):
        Item.objects.filter(pk=self.pk).update(upvotes=F("upvotes") + 1)
        self.upvotes += 1

    def decrement_vote_count(self):
        Item.objects.filter(pk=self.pk).update(upvotes=F("upvotes") - 1)
        self.upvotes -= 1

    def refresh_comment_count(self):
        count = self.comments.filter(deleted_at__isnull=True).count()
        Item.objects.filter(pk=self.pk).update(comment_count=count)
        self.comment_count = count

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())


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
    def upvote(cls, user, item, request):
        from common.request import parse_ip_address, parse_useragent

        if user.pk == item.author_id:
            return None, False

        vote, created = cls.objects.get_or_create(
            user=user,
            item=item,
            defaults={
                "ipaddress": parse_ip_address(request),
                "useragent": parse_useragent(request),
            },
        )
        if created:
            item.increment_vote_count()
            if item.author_id:
                item.author.increment_vote_count()
        return vote, created

    @classmethod
    def retract(cls, user, item):
        deleted, _ = cls.objects.filter(user=user, item=item).delete()
        if deleted:
            item.decrement_vote_count()
            if item.author_id:
                item.author.decrement_vote_count()
        return bool(deleted)

    @classmethod
    def voted_item_ids(cls, user, items):
        if not user.is_authenticated:
            return set()
        return set(cls.objects.filter(user=user, item__in=items).values_list("item_id", flat=True))
