from django.contrib.auth.hashers import make_password
from django.db import migrations


SYSTEM_USERS = (
    {"slug": "bot", "full_name": "Бот Базы", "email": "bot@basa.club"},
    {"slug": "moderator", "full_name": "Модератор", "email": "moderator@basa.club"},
    {"slug": "deleted", "full_name": "Юзер Удалился", "email": "deleted@basa.club"},
)


def create_system_users(apps, schema_editor):
    User = apps.get_model("users", "User")
    for account in SYSTEM_USERS:
        User.objects.get_or_create(
            slug=account["slug"],
            defaults={
                "email": account["email"],
                "full_name": account["full_name"],
                "password": make_password(None),
            },
        )


def delete_system_users(apps, schema_editor):
    User = apps.get_model("users", "User")
    slugs = [account["slug"] for account in SYSTEM_USERS]
    User.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_system_users, delete_system_users),
    ]
