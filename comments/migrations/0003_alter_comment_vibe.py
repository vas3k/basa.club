from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("comments", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="comment",
            name="vibe",
            field=models.CharField(
                blank=True,
                choices=[
                    ("good", "👍 Пробовал, доволен"),
                    ("bad", "👎 Пробовал, недоволен"),
                    ("neutral", "💬 Просто коммент"),
                ],
                max_length=16,
                null=True,
            ),
        ),
    ]
