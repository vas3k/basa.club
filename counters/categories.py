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


def counts(root_id, country_id="everywhere", city_id="everywhere"):
    country_id = country_id or "everywhere"
    city_id = city_id or "everywhere"
    try:
        version = VERSION_PATH.read_text().strip() or "0"
    except OSError:
        version = "0"

    key = f"category-counts:{version}:{country_id}:{city_id}:{root_id}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    fresh = calculate(root_id, country_id, city_id)
    cache.set(key, fresh, TIMEOUT)
    return fresh


def invalidate(root_id):
    # One item is counted in its city, its country, and the whole-world view.
    if root_id:
        VERSION_PATH.write_text(str(time.time()))


def refresh_all():
    """Drop every process's category cache and return whole-world root totals."""
    from categories.models import Category

    VERSION_PATH.write_text(str(time.time()))
    totals = {}
    for root_id in Category.objects.filter(parent__isnull=True).values_list("id", flat=True):
        fresh = calculate(root_id, "everywhere", "everywhere")
        totals[root_id] = fresh.get(root_id, 0)
    return totals


def calculate(root_id, country_id="everywhere", city_id="everywhere"):
    items = Item.visible_objects()
    if city_id and city_id != "everywhere":
        items = items.filter(Q(city_id=city_id) | Q(city__isnull=True, country_id=country_id))
    elif country_id and country_id != "everywhere":
        items = items.filter(country_id=country_id)

    grouped = (
        items
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
