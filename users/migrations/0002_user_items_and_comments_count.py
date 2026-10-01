from django.db import migrations, models
from django.db.models import Count, Q
from django.utils import timezone


def fill_counts(apps, schema_editor):
    User = apps.get_model("users", "User")
    Item = apps.get_model("items", "Item")
    Comment = apps.get_model("comments", "Comment")
    now = timezone.now()

    items = {
        row["author_id"]: row["n"]
        for row in Item.objects.filter(visibility="visible").filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now),
        ).values("author_id").annotate(n=Count("pk"))
    }
    comments = {
        row["author_id"]: row["n"]
        for row in Comment.objects.filter(deleted_at__isnull=True).values("author_id").annotate(n=Count("pk"))
    }

    users = list(User.objects.all())
    for user in users:
        user.items_count = items.get(user.pk, 0)
        user.comments_count = comments.get(user.pk, 0)
    if users:
        User.objects.bulk_update(users, ["items_count", "comments_count"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
        ("items", "0001_initial"),
        ("comments", "0003_comment_rating"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="items_count",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="user",
            name="comments_count",
            field=models.IntegerField(default=0),
        ),
        migrations.RunPython(fill_counts, migrations.RunPython.noop),
    ]
