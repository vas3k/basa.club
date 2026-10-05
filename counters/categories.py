import tempfile
import time
from pathlib import Path

from django.core.cache import cache
from django.db.models import Count, Q

from items.models import Item

# Counts for one root category and all of its subcategories, for one country and city.
# The version file is shared by every process, so a management command or an item
# change can drop the in-memory cache of the running server.
TIMEOUT = 60 * 60 * 24
VERSION_PATH = Path(tempfile.gettempdir()) / "vas3k-base-category-counts"


def version():
    try:
        return VERSION_PATH.read_text().strip() or "0"
    except OSError:
        return "0"


def bump_version():
    VERSION_PATH.write_text(str(time.time()))


def cache_key(root_id, country_id, city_id):
    return f"category-counts:{version()}:{country_id or 'everywhere'}:{city_id or 'everywhere'}:{root_id}"


def counts(root_id, country_id="everywhere", city_id="everywhere"):
    country_id = country_id or "everywhere"
    city_id = city_id or "everywhere"
    key = cache_key(root_id, country_id, city_id)
    cached = cache.get(key)
    if cached is not None:
        return cached
    fresh = calculate(root_id, country_id, city_id)
    cache.set(key, fresh, TIMEOUT)
    return fresh


def invalidate(root_id):
    # One item is counted in its city, its country, and the whole-world view.
    if root_id:
        bump_version()


def refresh_all():
    """Drop every process's category cache and return whole-world root totals."""
    from categories.models import Category

    bump_version()
    totals = {}
    for root_id in Category.objects.filter(parent__isnull=True).values_list("id", flat=True):
        fresh = calculate(root_id, "everywhere", "everywhere")
        totals[root_id] = fresh.get(root_id, 0)
    return totals


def in_place(items, country_id, city_id):
    """Items listed in this country and city. Worldwide items are not included."""
    if city_id and city_id != "everywhere":
        return items.filter(Q(city_id=city_id) | Q(city__isnull=True, country_id=country_id))
    if country_id and country_id != "everywhere":
        return items.filter(country_id=country_id)
    return items


def calculate(root_id, country_id="everywhere", city_id="everywhere"):
    grouped = (
        in_place(Item.visible_objects(), country_id, city_id)
        .filter(category_id=root_id)
        .order_by()
        .values("subcategory_id")
        .annotate(n=Count("pk"))
    )
    result = {root_id: 0}
    for row in grouped:
        result[root_id] += row["n"]
        if row["subcategory_id"]:
            result[row["subcategory_id"]] = row["n"]
    return result
