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
    item = models.OneToOneField(Item, related_name="search_index", null=True, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)
    index = SearchVectorField(null=False, editable=False)

    class Meta:
        db_table = "search_index"
        indexes = [
            GinIndex(fields=["index"], fastupdate=False),
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

        vector = _multi_search_vector("title", weight="A") \
            + _multi_search_vector("description", weight="B") \
            + _multi_search_vector("location", weight="B") \
            + _multi_search_vector("promo_code", weight="B") \
            + _multi_search_vector(Cast("contacts", TextField()), weight="B") \
            + _multi_search_vector("author__slug", weight="C") \
            + _multi_search_vector(_text("author__full_name"), weight="C") \
            + _multi_search_vector("category__name", weight="C") \
            + _multi_search_vector(_text("subcategory__name"), weight="C") \
            + _multi_search_vector(_text("country__name"), weight="C") \
            + _multi_search_vector(_text("city__name"), weight="C")

        cls.objects.update_or_create(
            item=item,
            defaults={
                "index": Item.objects.annotate(vector=vector).filter(pk=item.pk).values_list("vector", flat=True).first(),
            },
        )
        return True


def _text(field):
    # A null joined name makes the whole tsvector null.
    return Coalesce(F(field), Value(""), output_field=TextField())


def _multi_search_vector(*expressions, weight=None):
    return (
        SearchVector(*expressions, weight=weight, config="russian")
        + SearchVector(*expressions, weight=weight, config="simple")
    )
