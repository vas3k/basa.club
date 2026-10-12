from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("geo", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="geocountry",
            name="sort_order",
        ),
        migrations.RemoveField(
            model_name="geocity",
            name="sort_order",
        ),
        migrations.AlterField(
            model_name="geocountry",
            name="name",
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="geocity",
            name="name",
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterModelOptions(
            name="geocountry",
            options={"ordering": ["name"]},
        ),
        migrations.AlterModelOptions(
            name="geocity",
            options={"ordering": ["name"]},
        ),
    ]
