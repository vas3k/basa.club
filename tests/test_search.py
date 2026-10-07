from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from categories.models import Category
from geo.models import GeoCity, GeoCountry
from items.models import Item
from notifications.subscriptions import _query_matches
from search import search
from search.models import SearchIndex
from users.models import User


class SearchIndexTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="author@example.com",
            slug="author",
            full_name="Анна Ковалёва",
            password="secret",
        )
        self.category = Category.objects.create(id="dentists", name="Стоматология")
        self.country = GeoCountry.objects.create(id="serbia", name="Сербия")
        self.city = GeoCity.objects.create(id="belgrade", name="Белград", country=self.country)

    def make_item(self, **overrides):
        fields = dict(
            title="Приём без очереди",
            description="Обычный текст",
            location="Kralja Milana 42",
            promo_code="CLUB32",
            contacts=[{"type": "phone", "text": "79991234567", "comment": "с 10 до 18"}],
            category=self.category,
            country=self.country,
            city=self.city,
            author=self.author,
            visibility=Item.VISIBILITY_VISIBLE,
            published_at=timezone.now(),
        )
        fields.update(overrides)
        item = Item.objects.create(**fields)
        search.update_item_index(item)
        return item

    def test_listed_item_is_indexed_and_hidden_items_are_not(self):
        item = self.make_item()
        self.assertTrue(SearchIndex.objects.filter(pk=item.pk).exists())

        item.visibility = Item.VISIBILITY_DRAFT
        item.save()
        search.update_item_index(item)
        self.assertFalse(SearchIndex.objects.filter(pk=item.pk).exists())

        item.visibility = Item.VISIBILITY_VISIBLE
        item.expires_at = timezone.now() - timedelta(hours=1)
        item.save()
        search.update_item_index(item)
        self.assertFalse(SearchIndex.objects.filter(pk=item.pk).exists())

        item.expires_at = None
        item.save()
        search.update_item_index(item)
        item.delete(by=self.author)
        search.delete_item_index(item)
        self.assertFalse(SearchIndex.objects.filter(pk=item.pk).exists())

    def test_search_stems_russian_and_keeps_exact_tokens(self):
        item = self.make_item(title="Квартира на два месяца", description="")
        titles = list(
            search.filter_items(Item.visible_objects(), "квартиры")
            .order_by("-search_rank")
            .values_list("title", flat=True)
        )
        self.assertEqual(titles, ["Квартира на два месяца"])
        self.assertIn(item.pk, search.filter_items(Item.visible_objects(), "CLUB32").values_list("pk", flat=True))
        self.assertIn(item.pk, search.filter_items(Item.visible_objects(), "79991234567").values_list("pk", flat=True))
        self.assertNotIn(item.pk, search.filter_items(Item.visible_objects(), "whatsapp").values_list("pk", flat=True))

    def test_category_city_and_author_are_in_the_vector(self):
        item = self.make_item(title="Приём", description="")
        found = search.filter_items(Item.visible_objects(), "стоматология")
        self.assertIn(item.pk, found.values_list("pk", flat=True))
        self.assertIn(item.pk, search.filter_items(Item.visible_objects(), "белград").values_list("pk", flat=True))
        self.assertIn(item.pk, search.filter_items(Item.visible_objects(), "author").values_list("pk", flat=True))

    def test_empty_query_does_not_filter_and_odd_input_does_not_crash(self):
        self.make_item()
        self.assertEqual(search.filter_items(Item.visible_objects(), "  ").count(), 1)
        self.assertEqual(list(SearchIndex.search("")), [])
        self.assertEqual(list(SearchIndex.search('скидка "')), [])
        self.assertFalse(SearchIndex.search("zzznomatch").exists())

    def test_banned_author_is_removed_and_restored(self):
        item = self.make_item()
        self.author.is_banned_until = timezone.now() + timedelta(days=3)
        self.author.save(update_fields=["is_banned_until"])
        search.delete_author_index(self.author)
        self.assertFalse(SearchIndex.objects.filter(pk=item.pk).exists())

        self.author.is_banned_until = None
        self.author.save(update_fields=["is_banned_until"])
        search.update_item_index(item)
        self.assertTrue(SearchIndex.objects.filter(pk=item.pk).exists())

    def test_notification_match_uses_the_index(self):
        item = self.make_item(title="Квартира на два месяца", description="")
        subscription = type("Subscription", (), {"query": "квартиры"})()
        empty = type("Subscription", (), {"query": ""})()
        miss = type("Subscription", (), {"query": "zzznomatch"})()
        self.assertTrue(_query_matches(subscription, item))
        self.assertTrue(_query_matches(empty, item))
        self.assertFalse(_query_matches(miss, item))

    def test_listing_and_home_search(self):
        self.make_item(title="Квартира на два месяца", description="")
        reader = User.objects.create_user(email="reader@example.com", slug="reader", password="secret")
        self.client.force_login(reader)

        listing = self.client.get("/everywhere/everywhere/?query=квартиры&show_global=1")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual([item.title for item in listing.context["items"]], ["Квартира на два месяца"])

        home = self.client.get("/?query=квартиры")
        self.assertEqual(home.status_code, 200)
        self.assertEqual([item.title for item in home.context["all_items"]], ["Квартира на два месяца"])

        guests = self.client
        guests.logout()
        self.assertEqual(guests.get("/everywhere/everywhere/?query=квартиры").status_code, 302)

    def test_rebuild_command_drops_stale_rows(self):
        item = self.make_item()
        SearchIndex.objects.filter(pk=item.pk).delete()
        draft = self.make_item(title="Черновик")
        draft.visibility = Item.VISIBILITY_DRAFT
        draft.save()
        call_command("update_search_index")
        self.assertTrue(SearchIndex.objects.filter(pk=item.pk).exists())
        self.assertFalse(SearchIndex.objects.filter(pk=draft.pk).exists())
