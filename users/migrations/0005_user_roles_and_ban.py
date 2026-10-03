import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_user_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_banned_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="user",
            name="roles",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[("god", "Бог"), ("moderator", "Модератор")],
                    max_length=32,
                ),
                default=list,
            ),
        ),
    ]
