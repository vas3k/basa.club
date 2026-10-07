from django.db.models import FloatField, OuterRef, Subquery

from search.models import SearchIndex


def update_item_index(item):
    return SearchIndex.update_item_index(item)


def delete_item_index(item):
    SearchIndex.objects.filter(item=item).delete()


def delete_author_index(user):
    SearchIndex.objects.filter(item__author_id=user.pk).delete()


def filter_items(queryset, query):
    query = (query or "").strip()
    if not query:
        return queryset
    matches = SearchIndex.search(query).order_by().filter(item_id=OuterRef("pk"))
    return queryset.annotate(
        search_rank=Subquery(matches.values("rank")[:1], output_field=FloatField()),
    ).filter(search_rank__gt=0)


def item_matches(item, query):
    query = (query or "").strip()
    if not query:
        return True
    return SearchIndex.search(query).filter(item_id=item.pk).exists()
