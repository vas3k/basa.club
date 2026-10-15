from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("items", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="promo_code",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
    ]
