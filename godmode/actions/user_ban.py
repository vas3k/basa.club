from datetime import datetime, timedelta

from django import forms
from django.shortcuts import render
from django.utils import timezone

from items.models import Item
from notifications.telegram.users import user_banned
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


def ban_user(user, *, until, reason, comment, permanent):
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
    user_banned(user, reason=metadata["last_ban"]["reason"], comment=comment, until=until, is_permanent=permanent)
    return True


def unban_user(user):
    user.is_banned_until = None
    user.save(update_fields=["is_banned_until"])


def get_ban_action(request, obj, **context):
    user = target_user(obj)
    if not user:
        return render(request, "godmode/message.html", {
            **context,
            "title": "Автора нет",
            "message": "У этой записи нет автора, банить некого",
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
            "message": "У этой записи нет автора, банить некого",
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
    ban_user(user, until=until, reason=data["reason"], comment=data["comment"], permanent=permanent)
    return render(request, "godmode/message.html", {
        **context,
        "title": f"{name} забанен",
        "message": "Доступ закрыт навсегда" if permanent else f"Доступ закрыт на {data['days']} дн.",
    })
