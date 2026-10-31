from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from categories.models import Category
from geo.models import GeoCity, GeoCountry
from items.models import Item


class IndexSitemap(Sitemap):
    def items(self):
        return ["index"]

    def location(self, item):
        return reverse(item)


class CountrySitemap(Sitemap):
    def items(self):
        return GeoCountry.objects.order_by("id")

    def location(self, country):
        return f"/{country.id}/"


class CitySitemap(Sitemap):
    def items(self):
        return GeoCity.objects.order_by("country_id", "id")

    def location(self, city):
        return f"/{city.country_id}/{city.id}/"


class CategorySitemap(Sitemap):
    def items(self):
        countries = list(GeoCountry.objects.order_by("id").values_list("id", flat=True))
        cities = list(GeoCity.objects.order_by("country_id", "id").values_list("country_id", "id"))
        categories = list(Category.objects.order_by("sort_order", "id").values_list("id", "parent_id"))
        places = [("everywhere", "everywhere")]
        places.extend((country_id, "everywhere") for country_id in countries)
        places.extend(cities)
        return [
            (country_id, city_id, category_id, parent_id)
            for country_id, city_id in places
            for category_id, parent_id in categories
        ]

    def location(self, item):
        country_id, city_id, category_id, parent_id = item
        if parent_id:
            return f"/{country_id}/{city_id}/{parent_id}/{category_id}/"
        return f"/{country_id}/{city_id}/{category_id}/"


class ItemSitemap(Sitemap):
    def items(self):
        return (
            Item.visible_objects()
            .select_related(None)
            .only("id", "country_id", "city_id", "category_id", "subcategory_id", "updated_at")
            .order_by("id")
        )

    def location(self, item):
        return item.get_absolute_url()

    def lastmod(self, item):
        return item.updated_at


sitemaps = {
    "index": IndexSitemap,
    "countries": CountrySitemap,
    "cities": CitySitemap,
    "categories": CategorySitemap,
    "items": ItemSitemap,
}
