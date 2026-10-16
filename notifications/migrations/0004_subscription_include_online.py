from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notifications", "0003_subscription_with_global")]

    operations = [
        migrations.RenameField(
            model_name="subscription", old_name="with_global", new_name="include_online",
        ),
        migrations.AlterField(
            model_name="subscription", name="include_online",
            field=models.BooleanField(default=False, verbose_name="Включая онлайн"),
        ),
    ]
