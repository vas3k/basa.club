from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("items", "0004_item_moderator_comment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="updated_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
