from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent / "data"


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

    with open(DATA_DIR / "categories.yaml", encoding="utf-8") as file:
        categories = yaml.safe_load(file) or []
    create_tree(categories)


def seed_geo(GeoCountry, GeoCity):
    with open(DATA_DIR / "geo.yaml", encoding="utf-8") as file:
        catalog = yaml.safe_load(file) or []

    for country in catalog:
        country_id = geo_id(country.get("id"), country.get("name"))
        country_obj, _ = GeoCountry.objects.update_or_create(
            id=country_id,
            defaults={
                "name": country["name"],
                "icon": country.get("icon") or "",
            },
        )
        for city in country.get("cities") or []:
            GeoCity.objects.update_or_create(
                id=geo_id(city.get("id"), city.get("name")),
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
    # Historical migration models may not have the soft-delete manager.
    items = getattr(Item, "all_objects", Item.objects)
    users = getattr(User, "all_objects", User.objects)

    old = GeoCountry.objects.filter(pk="False").first()
    if old:
        new = GeoCountry.objects.filter(pk="no").first()
        if new is None:
            GeoCountry.objects.create(
                id="no",
                name=old.name,
                icon=old.icon,
                items_count=old.items_count,
            )
        else:
            GeoCountry.objects.filter(pk="no").update(items_count=new.items_count + old.items_count)
        GeoCity.objects.filter(country_id="False").update(country_id="no")
        items.filter(country_id="False").update(country_id="no")
        Subscription.objects.filter(country_id="False").update(country_id="no")
        old.delete()

    previous_countries = {country.id: country.name for country in GeoCountry.objects.all()}
    previous_cities = {
        city.id: (city.country_id, city.country.name, city.name)
        for city in GeoCity.objects.select_related("country")
    }
    country_ids = set()
    city_ids = set()
    with open(DATA_DIR / "geo.yaml", encoding="utf-8") as file:
        catalog = yaml.safe_load(file) or []

    for country in catalog:
        country_ids.add(geo_id(country.get("id"), country.get("name")))
        for city in country.get("cities") or []:
            city_ids.add(geo_id(city.get("id"), city.get("name")))
    seed_geo(GeoCountry, GeoCity)

    renamed_city_ids = []
    for country_id, old_name in previous_countries.items():
        country = GeoCountry.objects.filter(pk=country_id).first()
        if country and country.name != old_name:
            users.filter(country=old_name).update(country=country.name)

    for city_id, (old_country_id, old_country_name, old_city_name) in previous_cities.items():
        city = GeoCity.objects.select_related("country").filter(pk=city_id).first()
        if not city:
            continue
        if city.country_id != old_country_id:
            items.filter(city_id=city_id, country_id=old_country_id).update(country_id=city.country_id)
            Subscription.objects.filter(city_id=city_id, country_id=old_country_id).update(country_id=city.country_id)
        if city.name != old_city_name:
            renamed_city_ids.append(city_id)
            users.filter(country=city.country.name, city=old_city_name).update(city=city.name)
        elif city.country.name != old_country_name:
            users.filter(country=old_country_name, city=old_city_name).update(
                country=city.country.name,
                city=city.name,
            )

    if renamed_city_ids:
        item_ids = list(items.filter(city_id__in=renamed_city_ids).values_list("pk", flat=True))
        if item_ids:
            from items.models import Item as CurrentItem
            from search.models import SearchIndex

            for item in CurrentItem.all_objects.filter(pk__in=item_ids):
                SearchIndex.update_item_index(item)

    keep_cities = set(city_ids)
    keep_cities.update(items.exclude(city_id=None).values_list("city_id", flat=True))
    keep_cities.update(Subscription.objects.exclude(city_id=None).values_list("city_id", flat=True))
    for city in GeoCity.objects.exclude(id__in=keep_cities).select_related("country"):
        if users.filter(country=city.country.name, city=city.name).exists():
            keep_cities.add(city.id)
    GeoCity.objects.exclude(id__in=keep_cities).delete()

    keep_countries = set(country_ids)
    keep_countries.update(GeoCity.objects.values_list("country_id", flat=True))
    keep_countries.update(items.exclude(country_id=None).values_list("country_id", flat=True))
    keep_countries.update(Subscription.objects.exclude(country_id=None).values_list("country_id", flat=True))
    for country in GeoCountry.objects.exclude(id__in=keep_countries):
        if users.filter(country=country.name).exists():
            keep_countries.add(country.id)
    GeoCountry.objects.exclude(id__in=keep_countries).delete()


def geo_id(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"geo.yaml id for {label!r} must be a quoted string, got {value!r}"
        )
    return value.strip()
