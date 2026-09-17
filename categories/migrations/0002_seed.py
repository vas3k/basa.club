from django.db import migrations


def seed(apps, schema_editor):
    from common.seed import seed_categories
    seed_categories(apps.get_model("categories", "Category"))


class Migration(migrations.Migration):
    dependencies = [
        ("categories", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
