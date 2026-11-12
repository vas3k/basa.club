from datetime import datetime, timedelta

from django import forms
from django.db import transaction
from django.shortcuts import render
from django.utils import timezone
from django_q.tasks import async_task

from comments.models import Comment
from counters import counters
from items.models import Item
from notifications import notification
from search import search
from users.models import User

REASONS = (
    ("spam", "Спам"),
    ("scammer", "Мошенник"),
    ("low_quality", "Низкое качество"),
    ("aggression", "Агрессия"),
    ("ads", "Реклама"),
    ("other", "Другое"),
)


class UserBanForm(forms.Form):
    days = forms.IntegerField(label="На сколько дней", initial=7, min_value=1, required=False)
    reason = forms.ChoiceField(label="Причина", choices=REASONS)
    comment = forms.CharField(
        label="Комментарий",
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    is_permanent = forms.BooleanField(label="Забанить навечно", required=False)
    hide_items = forms.BooleanField(
        label="Переместить все посты в черновики",
        initial=False,
        required=False,
    )
    delete_comments = forms.BooleanField(
        label="Удалить все комментарии и ответы автора",
        help_text="Ответы других пользователей к удаляемым комментариям тоже будут скрыты.",
        initial=False,
        required=False,
    )
    is_unbanned = forms.BooleanField(required=False)

    def clean(self):
        data = super().clean()
        if data.get("is_unbanned") or data.get("is_permanent") or data.get("days"):
            return data
        self.add_error("days", "Укажите число дней или поставьте галочку «навечно»")
        return data


def target_user(obj):
    if isinstance(obj, User):
        return obj
    if isinstance(obj, Item):
        return obj.author
    return None


@transaction.atomic
def ban_user(user, *, until, reason, comment, permanent, hide_items=False, delete_comments=False, by=None):
    user = User.all_objects.get(id=user.id)
    if user.is_superuser:
        return False
    metadata = dict(user.metadata or {})
    metadata["last_ban"] = {
        "reason": dict(REASONS).get(reason, reason),
        "comment": comment or "",
        "permanent": permanent,
    }
    user.metadata = metadata
    user.is_banned_until = until
    user.save(update_fields=["metadata", "is_banned_until"])

    if hide_items or delete_comments:
        moderator_id = by.id if by else None
        transaction.on_commit(lambda: async_task(
            cleanup_banned_user_content, user.id, hide_items, delete_comments, moderator_id,
        ))

    transaction.on_commit(lambda: notification.user_banned(
        user,
        reason=metadata["last_ban"]["reason"],
        comment=comment,
        until=until,
        is_permanent=permanent,
    ))
    return True


@transaction.atomic
def cleanup_banned_user_content(user_id, hide_items, delete_comments, moderator_id):
    user = User.all_objects.filter(id=user_id).first()
    if not user or not user.is_banned:
        return

    if hide_items:
        for item in Item.objects.filter(author=user).exclude(visibility=Item.VISIBILITY_DRAFT):
            was_listed = item.is_listed
            item.visibility = Item.VISIBILITY_DRAFT
            item.save(update_fields=["visibility"])
            if was_listed:
                counters.item_hidden(item)
        search.delete_author_index(user)

    if delete_comments:
        moderator = User.all_objects.filter(id=moderator_id).first() if moderator_id else None
        comment_ids = list(Comment.objects.filter(author=user).order_by("created_at", "id").values_list("id", flat=True))
        for comment_id in comment_ids:
            authored_comment = Comment.objects.select_related("item").filter(id=comment_id).first()
            if authored_comment:
                authored_comment.delete(by=moderator)
                counters.comment_deleted(authored_comment)


@transaction.atomic
def unban_user(user):
    user = User.all_objects.get(id=user.id)
    user.is_banned_until = None
    user.save(update_fields=["is_banned_until"])
    for item in Item.objects.filter(author=user):
        search.update_item_index(item)


def get_ban_action(request, obj, **context):
    user = target_user(obj)
    if not user:
        return render(request, "godmode/message.html", {
            **context,
            "title": "Автора нет",
            "message": "У этого поста нет автора, банить некого",
        })
    return render(request, "godmode/actions/user_ban.html", {
        **context,
        "item": obj,
        "ban_user": user,
        "form": UserBanForm(),
    })


def post_ban_action(request, obj, **context):
    user = target_user(obj)
    if not user:
        return render(request, "godmode/message.html", {
            **context,
            "title": "Автора нет",
            "message": "У этого поста нет автора, банить некого",
        })

    form = UserBanForm(request.POST)
    if not form.is_valid():
        return render(request, "godmode/actions/user_ban.html", {
            **context,
            "item": obj,
            "ban_user": user,
            "form": form,
        })

    data = form.cleaned_data
    name = user.full_name or user.slug
    if user.is_superuser:
        return render(request, "godmode/message.html", {
            **context,
            "title": "Суперпользователей банить нельзя",
            "message": f"{name} остаётся на свободе",
        })

    if data["is_unbanned"]:
        unban_user(user)
        return render(request, "godmode/message.html", {
            **context,
            "title": f"{name} разбанен",
            "message": "Снова можно заходить на сайт",
        })

    now = timezone.now()
    permanent = bool(data["is_permanent"])
    until = datetime(9999, 12, 31, 23, 59, tzinfo=now.tzinfo) if permanent else now + timedelta(days=data["days"])
    ban_user(
        user,
        until=until,
        reason=data["reason"],
        comment=data["comment"],
        permanent=permanent,
        hide_items=data["hide_items"],
        delete_comments=data["delete_comments"],
        by=request.user,
    )
    return render(request, "godmode/message.html", {
        **context,
        "title": f"{name} забанен",
        "message": "Доступ закрыт навсегда" if permanent else f"Доступ закрыт на {data['days']} дн.",
    })
