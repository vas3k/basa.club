from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0006_item_view_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='prefix',
            field=models.CharField(
                blank=True,
                choices=[('ask', '#ищу')],
                max_length=16,
                null=True,
                verbose_name='Префикс',
            ),
        ),
    ]
