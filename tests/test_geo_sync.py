from django.test import TestCase
from django.utils import timezone

from categories.models import Category
from common.seed import sync_geo
from geo.models import GeoCity, GeoCountry
from items.models import Item
from notifications.models import Subscription
from users.models import User


class GeoSyncTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="author@example.com",
            slug="author",
            password="secret",
        )
        self.category = Category.objects.get(id="dentists")

    def test_sync_keeps_referenced_places_and_applies_catalog(self):
        germany = GeoCountry.objects.get(id="de")
        kept = GeoCity.objects.create(id="kept-ville", name="Старый город", country=germany)
        GeoCity.objects.create(id="gone-ville", name="Никому не нужен", country=germany)
        item = Item.objects.create(
            title="Запись к врачу",
            category=self.category,
            country=germany,
            city=kept,
            author=self.author,
            visibility=Item.VISIBILITY_VISIBLE,
            published_at=timezone.now(),
        )
        subscription = Subscription.objects.create(user=self.author, country=germany, city=kept)
        profile = User.objects.create_user(
            email="local@example.com",
            slug="local",
            password="secret",
            country="Германия",
            city="Старый город",
        )
        cordoba = GeoCity.objects.get(id="cordoba")
        cordoba.name = "Кордова"
        cordoba.save(update_fields=["name"])
        renamed = User.objects.create_user(
            email="cordoba@example.com",
            slug="cordoba-user",
            password="secret",
            country="Аргентина",
            city="Кордова",
        )
        norway = GeoCountry.objects.create(id="False", name="Норвегия", icon="🇳🇴", items_count=3)
        tromso = GeoCity.objects.create(id="tromso-x", name="Тромсё", country=norway)
        norway_item = Item.objects.create(
            title="Рыба в Тромсё",
            category=self.category,
            country=norway,
            city=tromso,
            author=self.author,
            visibility=Item.VISIBILITY_VISIBLE,
            published_at=timezone.now(),
        )

        sync_geo(GeoCountry, GeoCity, Item, Subscription, User)

        self.assertTrue(GeoCity.objects.filter(id="tirana").exists())
        self.assertFalse(GeoCity.objects.filter(id="gone-ville").exists())
        self.assertTrue(GeoCity.objects.filter(id="kept-ville", country_id="de").exists())
        item.refresh_from_db()
        subscription.refresh_from_db()
        profile.refresh_from_db()
        self.assertEqual(item.city_id, "kept-ville")
        self.assertEqual(item.country_id, "de")
        self.assertEqual(subscription.city_id, "kept-ville")
        self.assertEqual(profile.city, "Старый город")

        cordoba.refresh_from_db()
        renamed.refresh_from_db()
        self.assertEqual(cordoba.name, "Кордоба")
        self.assertEqual(renamed.city, "Кордоба")

        self.assertFalse(GeoCountry.objects.filter(id="False").exists())
        norway_item.refresh_from_db()
        self.assertEqual(norway_item.country_id, "no")
        self.assertEqual(norway_item.city_id, "tromso-x")
        self.assertEqual(GeoCity.objects.get(id="tromso-x").country_id, "no")
        self.assertGreaterEqual(GeoCountry.objects.get(id="no").items_count, 3)
