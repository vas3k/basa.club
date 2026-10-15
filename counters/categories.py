from django.core.cache import caches
from django.db.models import Count

from items.models import Item

# Counts for one root category and all of its subcategories, for one country and city.
TIMEOUT = 60 * 60 * 24
VERSION_KEY = "category_counts:version"

cache = caches["redis_cache"]


def counts(root_id, country_id="everywhere", city_id="everywhere"):
    country_id = country_id or "everywhere"
    city_id = city_id or "everywhere"
    version = cache.get(VERSION_KEY) or 0

    key = f"category_counts:{version}:{country_id}:{city_id}:{root_id}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    fresh = calculate(root_id, country_id, city_id)
    cache.set(key, fresh, TIMEOUT)
    return fresh


def invalidate(root_id):
    # One item is counted in its city, its country, or the everywhere bucket.
    if root_id:
        bump_version()


def refresh_all():
    """Drop the category cache and return root totals for items with no country."""
    from categories.models import Category

    bump_version()
    totals = {}
    for root_id in Category.objects.filter(parent__isnull=True).values_list("id", flat=True):
        fresh = calculate(root_id, "everywhere", "everywhere")
        totals[root_id] = fresh.get(root_id, 0)
    return totals


def calculate(root_id, country_id="everywhere", city_id="everywhere"):
    items = Item.visible_objects()
    if country_id == "everywhere":
        items = items.filter(country__isnull=True)
    elif city_id and city_id != "everywhere":
        items = items.filter(city_id=city_id)
    else:
        items = items.filter(country_id=country_id)

    grouped = (
        items
        .filter(category_id=root_id)
        .order_by()
        .values("subcategory_id")
        .annotate(n=Count("id"))
    )
    result = {root_id: 0}
    for row in grouped:
        result[root_id] += row["n"]
        if row["subcategory_id"]:
            result[row["subcategory_id"]] = row["n"]
    return result


def bump_version():
    # incr fails when the key is missing; add is the race-safe first write.
    try:
        cache.incr(VERSION_KEY)
    except ValueError:
        if not cache.add(VERSION_KEY, 1):
            cache.incr(VERSION_KEY)
