from django.db import migrations, models
from django.db.models import Q


def mark_global(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    Category.objects.filter(Q(pk="coupons") | Q(root_id="coupons") | Q(pk="psychologists")).update(is_global=True)


class Migration(migrations.Migration):

    dependencies = [
        ("categories", "0002_drop_items_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="is_global",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_global, migrations.RunPython.noop),
    ]
