from django.db import migrations


def sync(apps, schema_editor):
    from common.seed import sync_geo

    sync_geo(
        apps.get_model("geo", "GeoCountry"),
        apps.get_model("geo", "GeoCity"),
        apps.get_model("items", "Item"),
        apps.get_model("notifications", "Subscription"),
        apps.get_model("users", "User"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("geo", "0002_drop_geo_sort_order"),
        ("items", "0007_item_prefix"),
        ("notifications", "0002_alter_subscription_query"),
        ("users", "0006_user_bio_and_club_slug"),
        ("search", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(sync, migrations.RunPython.noop),
    ]
