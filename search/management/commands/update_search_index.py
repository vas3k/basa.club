from django.core.management.base import BaseCommand

from items.models import Item
from search import search
from search.models import SearchIndex


class Command(BaseCommand):
    help = "Rebuild the full-text index for every item. No other models are indexed."

    def handle(self, *args, **options):
        ids = list(Item.all_objects.values_list("pk", flat=True))
        indexed = 0
        for start in range(0, len(ids), 200):
            batch = Item.all_objects.filter(pk__in=ids[start:start + 200])
            for item in batch:
                if search.update_item_index(item):
                    indexed += 1
        if ids:
            removed, _ = SearchIndex.objects.filter(item__isnull=False).exclude(item_id__in=ids).delete()
        else:
            removed, _ = SearchIndex.objects.filter(item__isnull=False).delete()
        self.stdout.write(self.style.SUCCESS(
            f"Search index rebuilt: {indexed} items indexed, {removed} rows removed"
        ))
