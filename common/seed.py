from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent / "data"


def load_yaml(filename):
    with open(DATA_DIR / filename, encoding="utf-8") as file:
        return yaml.safe_load(file) or []


def seed_categories(Category):
    def create_tree(nodes, parent=None, root=None):
        for index, node in enumerate(nodes):
            if "is_global" in node:
                is_global = bool(node["is_global"])
            else:
                is_global = bool(parent and getattr(parent, "is_global", False))
            defaults = {
                "name": node["name"],
                "icon": node.get("icon") or "",
                "description": node.get("description") or "",
                "parent": parent,
                "root": root,
                "sort_order": node.get("sort_order", index),
            }
            if any(field.name == "is_global" for field in Category._meta.fields):
                defaults["is_global"] = is_global
            category, _ = Category.objects.update_or_create(
                id=node["id"],
                defaults=defaults,
            )
            create_tree(node.get("children") or [], parent=category, root=root or category)

    create_tree(load_yaml("categories.yaml"))


def seed_geo(GeoCountry, GeoCity):
    for country in load_yaml("geo.yaml"):
        country_id = _geo_id(country.get("id"), country.get("name"))
        country_obj, _ = GeoCountry.objects.update_or_create(
            id=country_id,
            defaults={
                "name": country["name"],
                "icon": country.get("icon") or "",
            },
        )
        for city in country.get("cities") or []:
            GeoCity.objects.update_or_create(
                id=_geo_id(city.get("id"), city.get("name")),
                defaults={
                    "name": city["name"],
                    "icon": city.get("icon") or "",
                    "country": country_obj,
                },
            )


def sync_geo(GeoCountry, GeoCity, Item, Subscription, User):
    """Upsert geo.yaml and drop catalog rows nothing points at anymore.

    Listings, subscriptions, and profile places keep their country and city.
    An unquoted YAML `no` was loaded as false, so Norway may be stored as "False".
    """
    for old_id, new_id in (("False", "no"),):
        _move_country(GeoCountry, GeoCity, Item, Subscription, old_id, new_id)

    previous_countries = {country.id: country.name for country in GeoCountry.objects.all()}
    previous_cities = {
        city.id: (city.country_id, city.country.name, city.name)
        for city in GeoCity.objects.select_related("country")
    }
    catalog = _geo_catalog()
    seed_geo(GeoCountry, GeoCity)
    _rewrite_place_names(GeoCountry, GeoCity, Item, Subscription, User, previous_countries, previous_cities)
    _drop_unreferenced_geo(GeoCountry, GeoCity, Item, Subscription, User, catalog)


def _geo_id(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"geo.yaml id for {label!r} must be a quoted string, got {value!r}"
        )
    return value.strip()


def _geo_catalog():
    countries = set()
    cities = set()
    for country in load_yaml("geo.yaml"):
        countries.add(_geo_id(country.get("id"), country.get("name")))
        for city in country.get("cities") or []:
            cities.add(_geo_id(city.get("id"), city.get("name")))
    return countries, cities


def _rows(model):
    return getattr(model, "all_objects", model.objects)


def _move_country(GeoCountry, GeoCity, Item, Subscription, old_id, new_id):
    old = GeoCountry.objects.filter(pk=old_id).first()
    if not old or old_id == new_id:
        return
    new = GeoCountry.objects.filter(pk=new_id).first()
    if new is None:
        GeoCountry.objects.create(
            id=new_id,
            name=old.name,
            icon=old.icon,
            items_count=old.items_count,
        )
    else:
        GeoCountry.objects.filter(pk=new_id).update(items_count=new.items_count + old.items_count)
    GeoCity.objects.filter(country_id=old_id).update(country_id=new_id)
    _rows(Item).filter(country_id=old_id).update(country_id=new_id)
    Subscription.objects.filter(country_id=old_id).update(country_id=new_id)
    old.delete()


def _rewrite_place_names(GeoCountry, GeoCity, Item, Subscription, User, previous_countries, previous_cities):
    renamed_city_ids = []
    for country_id, old_name in previous_countries.items():
        country = GeoCountry.objects.filter(pk=country_id).first()
        if country and country.name != old_name:
            _rows(User).filter(country=old_name).update(country=country.name)

    for city_id, (old_country_id, old_country_name, old_city_name) in previous_cities.items():
        city = GeoCity.objects.select_related("country").filter(pk=city_id).first()
        if not city:
            continue
        if city.country_id != old_country_id:
            _rows(Item).filter(city_id=city_id, country_id=old_country_id).update(country_id=city.country_id)
            Subscription.objects.filter(city_id=city_id, country_id=old_country_id).update(country_id=city.country_id)
        if city.name != old_city_name:
            renamed_city_ids.append(city_id)
            _rows(User).filter(country=city.country.name, city=old_city_name).update(city=city.name)
        elif city.country.name != old_country_name:
            _rows(User).filter(country=old_country_name, city=old_city_name).update(
                country=city.country.name,
                city=city.name,
            )

    if renamed_city_ids:
        _reindex_items(_rows(Item).filter(city_id__in=renamed_city_ids).values_list("pk", flat=True))


def _reindex_items(item_ids):
    item_ids = list(item_ids)
    if not item_ids:
        return
    from items.models import Item
    from search.models import SearchIndex

    for item in Item.all_objects.filter(pk__in=item_ids):
        SearchIndex.update_item_index(item)


def _drop_unreferenced_geo(GeoCountry, GeoCity, Item, Subscription, User, catalog):
    country_ids, city_ids = catalog
    keep_cities = set(city_ids)
    keep_cities.update(_rows(Item).exclude(city_id=None).values_list("city_id", flat=True))
    keep_cities.update(Subscription.objects.exclude(city_id=None).values_list("city_id", flat=True))
    for city in GeoCity.objects.exclude(id__in=keep_cities).select_related("country"):
        if _rows(User).filter(country=city.country.name, city=city.name).exists():
            keep_cities.add(city.id)
    GeoCity.objects.exclude(id__in=keep_cities).delete()

    keep_countries = set(country_ids)
    keep_countries.update(GeoCity.objects.values_list("country_id", flat=True))
    keep_countries.update(_rows(Item).exclude(country_id=None).values_list("country_id", flat=True))
    keep_countries.update(Subscription.objects.exclude(country_id=None).values_list("country_id", flat=True))
    for country in GeoCountry.objects.exclude(id__in=keep_countries):
        if _rows(User).filter(country=country.name).exists():
            keep_countries.add(country.id)
    GeoCountry.objects.exclude(id__in=keep_countries).delete()
