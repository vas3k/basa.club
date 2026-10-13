from urllib.parse import urlencode
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.urls import reverse


class Subscription(models.Model):
    QUERY_MAX_LENGTH = 64

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="subscriptions",
        on_delete=models.CASCADE,
    )
    country = models.ForeignKey(
        "geo.GeoCountry",
        null=True,
        blank=True,
        related_name="subscriptions",
        on_delete=models.CASCADE,
    )
    city = models.ForeignKey(
        "geo.GeoCity",
        null=True,
        blank=True,
        related_name="subscriptions",
        on_delete=models.CASCADE,
    )
    category = models.ForeignKey(
        "categories.Category",
        null=True,
        blank=True,
        related_name="subscriptions",
        on_delete=models.CASCADE,
    )
    query = models.CharField(max_length=QUERY_MAX_LENGTH, blank=True, default="")
    with_global = models.BooleanField(default=False, verbose_name="Глобальные")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "subscriptions"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "country", "city", "category", "query"],
                name="subscriptions_user_target_uniq",
                nulls_distinct=False,
            ),
            models.CheckConstraint(
                condition=models.Q(city__isnull=True) | models.Q(country__isnull=False),
                name="subscriptions_city_has_country",
            ),
        ]

    def __str__(self):
        return self.label

    @property
    def label(self):
        if self.city_id and self.country_id:
            place = f"{self.city.name}, {self.country.name}"
        elif self.country_id:
            place = self.country.name
        else:
            place = "Весь мир"
        parts = []
        if self.query:
            parts.append(f"«{self.query}»")
        if self.category_id:
            parts.append(self.category.name)
        parts.append(place)
        return " · ".join(parts)

    @property
    def listing_url(self):
        country = self.country_id or "everywhere"
        city = self.city_id or "everywhere"
        if self.category_id and self.category.parent_id:
            path = reverse("listing_subcategory", kwargs={
                "country": country,
                "city": city,
                "category": self.category.root_id or self.category.parent_id,
                "subcategory": self.category_id,
            })
        elif self.category_id:
            path = reverse("listing_category", kwargs={
                "country": country,
                "city": city,
                "category": self.category_id,
            })
        elif country == "everywhere" and city == "everywhere":
            path = reverse("index")
        else:
            path = reverse("listing", kwargs={"country": country, "city": city})
        params = {}
        if self.query:
            params["query"] = self.query
        if self.with_global:
            params["show_global"] = "1"
        if params:
            return f"{path}?{urlencode(params)}"
        return path
