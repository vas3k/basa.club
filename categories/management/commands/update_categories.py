from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.db.models import Q

from categories.models import Category
from common.seed import DATA_DIR
from items.models import Item
from notifications.models import Subscription

# categories.yaml stays the catalog until the tree stops changing. Take this command
# off the production boot path when that happens.


class Command(BaseCommand):
    help = (
        "Update categories from categories.yaml. "
        "Listings in a removed category move onto the broader parent category. "
        "Items are never deleted."
    )

    def handle(self, *args, **options):
        try:
            summary, notes, clashes = sync_categories()
        except Exception as error:
            self.stderr.write(f"update_categories failed: {error}")
            return

        for note in notes:
            self.stdout.write(note)
        for clash in clashes:
            self.stderr.write(f"clash: {clash}")
        self.stdout.write(summary)


def sync_categories():
    clashes = []
    records = load_records(clashes)
    if records is None:
        return "update_categories skipped", [], clashes

    before = {category.id: category for category in Category.objects.all()}
    desired_ids = set()
    renamed = set()
    created = 0
    updated = 0

    for record in records:
        old = before.get(record["id"])
        try:
            with transaction.atomic():
                category, was_created = Category.objects.update_or_create(
                    id=record["id"],
                    defaults=record["defaults"],
                )
        except Exception as error:
            clashes.append(f"{record['id']}: {error}")
            desired_ids.add(record["id"])
            continue

        desired_ids.add(category.id)
        if was_created:
            created += 1
            continue
        if old and any(getattr(old, field) != value for field, value in record["defaults"].items()):
            updated += 1
            if old.name != record["defaults"]["name"]:
                renamed.add(record["id"])

    moved_item_ids = set()
    notes = []
    removed = 0

    for category in removal_order(Category.objects.exclude(id__in=desired_ids)):
        try:
            removed += retire_category(category, desired_ids, moved_item_ids, notes, clashes)
        except Exception as error:
            clashes.append(f"{category.id}: {error}")

    reindex_items(moved_item_ids, renamed, clashes)
    from counters.categories import invalidate
    invalidate("catalog")

    summary = (
        f"update_categories: {created} created, {updated} updated, "
        f"{removed} removed, {len(moved_item_ids)} items moved, {len(clashes)} clashes"
    )
    return summary, notes, clashes


def load_records(clashes):
    path = DATA_DIR / "categories.yaml"
    try:
        import yaml
        with open(path, encoding="utf-8") as file:
            catalog = yaml.safe_load(file)
    except Exception as error:
        clashes.append(f"could not read {path.name}: {error}")
        return None

    if not isinstance(catalog, list) or not catalog:
        clashes.append(f"{path.name} is empty, existing categories were left untouched")
        return None

    records = []
    seen = set()
    collect_records(catalog, None, None, False, records, seen, clashes)
    if not records:
        clashes.append(f"{path.name} has no usable categories, existing categories were left untouched")
        return None
    return records


def collect_records(nodes, parent_id, root_id, inherited_global, records, seen, clashes):
    if not isinstance(nodes, list):
        clashes.append(f"children of {parent_id or 'the root'} are not a list")
        return

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            clashes.append(f"skipped a non-mapping category under {parent_id or 'the root'}")
            continue

        category_id = node.get("id")
        label = node.get("name") or parent_id or "the root"
        if not isinstance(category_id, str) or not category_id.strip():
            clashes.append(f"skipped {label!r}: id must be a string")
            continue
        category_id = category_id.strip()
        if len(category_id) > 64:
            clashes.append(f"skipped {category_id!r}: id is longer than 64 characters")
            continue
        if category_id in seen or category_id == parent_id:
            clashes.append(f"skipped duplicate id {category_id}")
            continue

        name = node.get("name")
        if not isinstance(name, str) or not name.strip():
            clashes.append(f"skipped {category_id}: name is missing")
            continue
        name = name.strip()
        if len(name) > 255:
            clashes.append(f"{category_id}: name is longer than 255 characters")
            name = name[:255]

        icon = node.get("icon") or ""
        if not isinstance(icon, str):
            clashes.append(f"{category_id}: icon is not text")
            icon = ""
        if len(icon) > 255:
            clashes.append(f"{category_id}: icon is longer than 255 characters")
            icon = icon[:255]

        description = node.get("description") or ""
        if not isinstance(description, str):
            clashes.append(f"{category_id}: description is not text")
            description = ""

        if "is_global" in node:
            is_global = bool(node["is_global"])
        else:
            is_global = inherited_global

        seen.add(category_id)
        records.append({
            "id": category_id,
            "defaults": {
                "name": name,
                "icon": icon,
                "description": description,
                "parent_id": parent_id,
                "root_id": root_id,
                "sort_order": index,
                "is_global": is_global,
            },
        })
        collect_records(
            node.get("children") or [],
            category_id,
            root_id or category_id,
            is_global,
            records,
            seen,
            clashes,
        )


def removal_order(categories):
    categories = list(categories)
    by_id = {category.id: category for category in Category.objects.all()}

    def depth(category):
        level = 0
        seen = set()
        current = category
        while current.parent_id and current.parent_id not in seen:
            seen.add(current.id)
            parent = by_id.get(current.parent_id)
            if parent is None:
                break
            current = parent
            level += 1
        return level

    return sorted(categories, key=depth, reverse=True)


def retire_category(category, desired_ids, moved_item_ids, notes, clashes):
    items = Item.all_objects.filter(Q(category_id=category.id) | Q(subcategory_id=category.id))
    destination = broader_category(category, desired_ids)
    item_ids = list(items.values_list("pk", flat=True))

    if item_ids and destination is None:
        clashes.append(f"kept {category.id}: {len(item_ids)} items have no broader category")
        return 0

    if item_ids:
        place_items(items, destination)
        moved_item_ids.update(item_ids)
        notes.append(f"moved {len(item_ids)} items from {category.id} to {destination.id}")

    move_subscriptions(category, destination, clashes)

    if Category.objects.filter(Q(parent_id=category.id) | Q(root_id=category.id)).exclude(pk=category.id).exists():
        clashes.append(f"kept {category.id}: other categories still point at it")
        return 0

    if Item.all_objects.filter(Q(category_id=category.id) | Q(subcategory_id=category.id)).exists():
        clashes.append(f"kept {category.id}: items still point at it")
        return 0

    category.delete()
    return 1


def broader_category(category, desired_ids):
    """Parent to keep the listings on. Prefer a category that is still in the file."""
    fallback = None
    current = category
    seen = set()
    while current.parent_id and current.parent_id not in seen:
        seen.add(current.id)
        parent = Category.objects.filter(pk=current.parent_id).first()
        if parent is None:
            break
        fallback = parent
        if parent.id in desired_ids:
            return parent
        current = parent
    return fallback


def place_items(items, destination):
    if destination.parent_id:
        root_id = destination.root_id or destination.parent_id
        items.update(category_id=root_id, subcategory_id=destination.id)
        return
    items.update(category_id=destination.id, subcategory_id=None)


def move_subscriptions(category, destination, clashes):
    target_id = destination.id if destination is not None else None
    for subscription in Subscription.objects.filter(category_id=category.id):
        try:
            with transaction.atomic():
                subscription.category_id = target_id
                subscription.save(update_fields=["category_id"])
        except IntegrityError:
            where = target_id or "every category"
            clashes.append(
                f"subscription {subscription.pk} already covers {where}; dropped the duplicate"
            )
            subscription.delete()


def reindex_items(moved_item_ids, renamed_ids, clashes):
    if not moved_item_ids and not renamed_ids:
        return

    from search import search

    if renamed_ids:
        queryset = Item.all_objects.filter(
            Q(pk__in=moved_item_ids) | Q(category_id__in=renamed_ids) | Q(subcategory_id__in=renamed_ids)
        )
    else:
        queryset = Item.all_objects.filter(pk__in=moved_item_ids)

    try:
        for item in queryset.iterator():
            search.update_item_index(item)
    except Exception as error:
        clashes.append(f"search index: {error}")
