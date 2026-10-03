from django.db import migrations, models


def _text(value):
    if isinstance(value, dict):
        value = value.get("name") or value.get("title") or ""
    if value is None:
        return ""
    return str(value).strip()


def fold_profiles(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.all().iterator():
        update_fields = []
        headline = ", ".join(part for part in (_text(user.position), _text(user.company)) if part)
        if headline:
            bio = _text(user.bio)
            user.bio = "\n\n".join(part for part in (headline, bio) if part)
            update_fields.append("bio")

        cache = user.profile_cache if isinstance(user.profile_cache, dict) else {}
        member = cache.get("user") if isinstance(cache.get("user"), dict) else {}
        slug = _text(member.get("slug")) or _text(cache.get("slug"))
        if slug:
            user.club_slug = slug[:64]
            update_fields.append("club_slug")

        if update_fields:
            user.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_user_roles_and_ban"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="club_slug",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.RunPython(fold_profiles, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="user",
            name="company",
        ),
        migrations.RemoveField(
            model_name="user",
            name="position",
        ),
        migrations.RemoveField(
            model_name="user",
            name="profile_cache",
        ),
    ]
