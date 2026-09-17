from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent / "data"


def load_yaml(filename):
    with open(DATA_DIR / filename, encoding="utf-8") as file:
        return yaml.safe_load(file) or []


def seed_categories(Category):
    def create_tree(nodes, parent=None, root=None):
        for index, node in enumerate(nodes):
            category, _ = Category.objects.update_or_create(
                id=node["id"],
                defaults={
                    "name": node["name"],
                    "icon": node.get("icon") or "",
                    "description": node.get("description") or "",
                    "parent": parent,
                    "root": root,
                    "sort_order": node.get("sort_order", index),
                },
            )
            create_tree(node.get("children") or [], parent=category, root=root or category)

    create_tree(load_yaml("categories.yaml"))


def seed_geo(GeoCountry, GeoCity):
    for country_index, country in enumerate(load_yaml("geo.yaml")):
        country_obj, _ = GeoCountry.objects.update_or_create(
            id=country["id"],
            defaults={
                "name": country["name"],
                "icon": country.get("icon") or "",
                "sort_order": country.get("sort_order", country_index),
            },
        )
        for city_index, city in enumerate(country.get("cities") or []):
            GeoCity.objects.update_or_create(
                id=city["id"],
                defaults={
                    "name": city["name"],
                    "icon": city.get("icon") or "",
                    "country": country_obj,
                    "sort_order": city.get("sort_order", city_index),
                },
            )
