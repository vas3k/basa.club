from datetime import timedelta

from django import forms
from django.shortcuts import render
from django.utils import timezone

from users.models import User

PERMANENT_BAN_DAYS = 9999


class UserBanForm(forms.Form):
    days = forms.IntegerField(
        label="На сколько дней",
        initial=7,
        min_value=1,
        required=False,
    )
    reason = forms.CharField(
        label="Причина",
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    is_permanent = forms.BooleanField(
        label="Забанить навечно",
        required=False,
    )
    is_unbanned = forms.BooleanField(
        label="Разбанить",
        required=False,
    )


def ban_user(user: User, days: int, reason: str) -> bool:
    if days <= 0 or user.is_god:
        return False

    metadata = dict(user.metadata or {})
    metadata["last_ban"] = {
        "days": days,
        "reason": reason or "",
    }
    user.metadata = metadata
    user.is_banned_until = timezone.now() + timedelta(days=days)
    user.save(update_fields=["metadata", "is_banned_until"])
    return True


def unban_user(user: User):
    user.is_banned_until = None
    user.save(update_fields=["is_banned_until"])


def get_ban_action(request, user: User, **context):
    return render(request, "godmode/actions/user_ban.html", {
        **context,
        "item": user,
        "form": UserBanForm(),
    })


def post_ban_action(request, user: User, **context):
    form = UserBanForm(request.POST)
    if not form.is_valid():
        return render(request, "godmode/actions/user_ban.html", {
            **context,
            "item": user,
            "form": form,
        })

    data = form.cleaned_data
    if user.is_god:
        return render(request, "godmode/message.html", {
            **context,
            "title": "Богов банить нельзя",
            "message": f"{user.full_name or user.slug} остаётся на свободе",
        })

    if data["is_unbanned"]:
        unban_user(user)
        return render(request, "godmode/message.html", {
            **context,
            "title": f"{user.full_name or user.slug} разбанен",
            "message": "Снова можно писать и комментировать",
        })

    if data["is_permanent"]:
        banned = ban_user(user, days=PERMANENT_BAN_DAYS, reason=data["reason"] or "Навсегда")
    elif data["days"]:
        banned = ban_user(user, days=data["days"], reason=data["reason"])
    else:
        banned = False

    return render(request, "godmode/message.html", {
        **context,
        "title": f"{user.full_name or user.slug} забанен" if banned else "Бан не применился",
        "message": "Доступ закрыт до окончания срока" if banned else "Укажите число дней или поставьте галочку",
    })
