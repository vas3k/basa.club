from uuid import uuid4

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, SearchVectorField
from django.db import models
from django.db.models import F, TextField, Value
from django.db.models.functions import Cast, Coalesce

from items.models import Item
from users.models import User


class SearchIndex(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    item = models.ForeignKey(
        Item,
        related_name="search_indexes",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    updated_at = models.DateTimeField(auto_now=True)
    index = SearchVectorField(null=False, editable=False)

    class Meta:
        db_table = "search_index"
        indexes = [
            GinIndex(fields=["index"], name="search_index_gin", fastupdate=False),
        ]

    def __str__(self):
        return self.item.title if self.item_id else str(self.pk)

    @classmethod
    def search(cls, query):
        query = (query or "").strip()
        if not query:
            return cls.objects.none()

        plain = SearchQuery(query, config="simple", search_type="websearch")
        stemmed = SearchQuery(query, config="russian", search_type="websearch")
        return cls.objects.annotate(
            rank=SearchRank(F("index"), plain, cover_density=True) * 2
            + SearchRank(F("index"), stemmed, cover_density=True),
        ).filter(index=plain | stemmed, rank__gt=0)

    @classmethod
    def update_item_index(cls, item):
        author = User.all_objects.filter(pk=item.author_id).first()
        if item.deleted_at or not item.is_listed or not author or author.deleted_at or author.is_banned:
            cls.objects.filter(item=item).delete()
            return False

        # Null names from optional joins must not erase the rest of the search vector.
        fields = (
            ("title", "A"),
            ("description", "B"),
            ("location", "B"),
            ("promo_code", "B"),
            (Cast("contacts", TextField()), "B"),
            ("author__slug", "C"),
            (Coalesce(F("author__full_name"), Value(""), output_field=TextField()), "C"),
            ("category__name", "C"),
            (Coalesce(F("subcategory__name"), Value(""), output_field=TextField()), "C"),
            (Coalesce(F("country__name"), Value(""), output_field=TextField()), "C"),
            (Coalesce(F("city__name"), Value(""), output_field=TextField()), "C"),
        )
        vector = None
        for expression, weight in fields:
            field_vector = (
                SearchVector(expression, weight=weight, config="russian")
                + SearchVector(expression, weight=weight, config="simple")
            )
            vector = field_vector if vector is None else vector + field_vector

        cls.objects.update_or_create(
            item=item,
            defaults={
                "index": Item.objects.annotate(vector=vector).filter(pk=item.pk).values_list("vector", flat=True).first(),
            },
        )
        return True
