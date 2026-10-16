from django.db import migrations


def add_online_country(apps, schema_editor):
    Country = apps.get_model("geo", "GeoCountry")
    Country.objects.using(schema_editor.connection.alias).update_or_create(
        id="online", defaults={"name": "Онлайн и ремоут", "icon": "💻"},
    )


class Migration(migrations.Migration):
    dependencies = [("geo", "0001_initial")]

    operations = [migrations.RunPython(add_online_country, migrations.RunPython.noop)]
