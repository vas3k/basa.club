from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("items", "0003_item_location_contacts_promo"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="images",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
