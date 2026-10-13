from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="with_global",
            field=models.BooleanField(default=False, verbose_name="Глобальные"),
        ),
    ]
