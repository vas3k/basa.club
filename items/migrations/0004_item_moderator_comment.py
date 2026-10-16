from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("items", "0003_promo_code_max_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="moderator_comment",
            field=models.TextField(blank=True, null=True, verbose_name="Комментарий модератора"),
        ),
    ]
