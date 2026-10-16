from django.db import migrations, models


def enable_online_for_coupons(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    Category.objects.using(schema_editor.connection.alias).filter(id="coupons").update(
        metadata={"include_online": True},
    )


class Migration(migrations.Migration):
    dependencies = [("categories", "0002_remove_category_is_global")]

    operations = [
        migrations.AddField(
            model_name="category",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(enable_online_for_coupons, migrations.RunPython.noop),
    ]
