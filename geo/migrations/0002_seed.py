from django.db import migrations


def seed(apps, schema_editor):
    from common.seed import seed_geo
    seed_geo(apps.get_model("geo", "GeoCountry"), apps.get_model("geo", "GeoCity"))


class Migration(migrations.Migration):
    dependencies = [
        ("geo", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
