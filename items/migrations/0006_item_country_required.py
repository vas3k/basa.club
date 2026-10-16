from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import migrations, models
from django.db.models import Count, F, Q, Value
from django.db.models.expressions import CombinedExpression
from django.utils import timezone
import django.db.models.deletion


def move_worldwide_items(apps, schema_editor):
    alias = schema_editor.connection.alias
    Item = apps.get_model("items", "Item")
    Country = apps.get_model("geo", "GeoCountry")
    City = apps.get_model("geo", "GeoCity")
    SearchIndex = apps.get_model("search", "SearchIndex")
    items = Item._base_manager.using(alias)

    # The old entries had no country text in their search vector.
    country_vector = (
        SearchVector(Value("Онлайн и ремоут"), weight="C", config="russian")
        + SearchVector(Value("Онлайн и ремоут"), weight="C", config="simple")
    )
    SearchIndex.objects.using(alias).filter(item__country__isnull=True).update(
        index=CombinedExpression(F("index"), "||", country_vector, output_field=SearchVectorField()),
    )
    items.filter(country__isnull=True).update(country_id="online", city_id=None)

    listed = items.filter(deleted_at__isnull=True, visibility="visible").filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
    ).order_by()
    Country.objects.using(alias).update(items_count=0)
    for row in listed.values("country_id").annotate(total=Count("id")):
        Country.objects.using(alias).filter(id=row["country_id"]).update(items_count=row["total"])
    City.objects.using(alias).update(items_count=0)
    for row in listed.exclude(city_id=None).values("city_id").annotate(total=Count("id")):
        City.objects.using(alias).filter(id=row["city_id"]).update(items_count=row["total"])


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("items", "0005_item_updated_at"),
        ("geo", "0002_online_country"),
        ("search", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(move_worldwide_items, migrations.RunPython.noop, atomic=True),
        migrations.AlterField(
            model_name="item",
            name="country",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="items",
                to="geo.geocountry",
            ),
        ),
    ]
