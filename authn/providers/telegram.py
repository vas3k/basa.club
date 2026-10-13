from django.conf import settings
from django.db import transaction
from django.shortcuts import render
from django.urls import reverse
from django.utils.text import slugify

from authn.forms import TelegramSignupForm
from authn.models import Code
from common.request import parse_ip_address, parse_useragent
from users.models import User


class TelegramAuthError(Exception):
    def __init__(self, message):
        self.message = message


def bot_url(request, user=None):
    address = parse_ip_address(request)
    auth_code = Code.create_for_user(
        user=user,
        recipient=address or "telegram",
        ipaddress=address,
        useragent=parse_useragent(request),
    )
    return f"{settings.TELEGRAM_BOT_URL}?start={auth_code.code}"


def confirm(code, data):
    telegram_id = str((data or {}).get("id") or "").strip()
    if not telegram_id.isdigit():
        raise TelegramAuthError("Telegram не прислал id. Попробуйте ещё раз.")
    payload = {
        "id": telegram_id,
        "username": data.get("username"),
        "first_name": data.get("first_name"),
        "last_name": data.get("last_name"),
        "language_code": data.get("language_code"),
    }

    auth_code = Code.objects.filter(code=(code or "").strip().upper()).select_related("user").first()
    if not auth_code or auth_code.is_expired():
        page = f"{settings.APP_HOST.rstrip('/')}{reverse('bot')}"
        raise TelegramAuthError(f"Ссылка устарела. Откройте бота заново со страницы привязки:\n{page}")

    previous = str((auth_code.telegram_data or {}).get("id") or "")
    if previous and previous != telegram_id:
        raise TelegramAuthError("Этот код уже подтвердил другой Telegram.")

    account = User.objects.filter(telegram_id=telegram_id).first()
    if auth_code.user_id:
        if account and account.pk != auth_code.user_id:
            raise TelegramAuthError("Этот Telegram уже привязан к другому профилю.")
        user = auth_code.user
        user.telegram_id = telegram_id
        user.telegram_data = payload
        if not user.full_name:
            name = " ".join(part for part in (payload.get("first_name"), payload.get("last_name")) if part).strip()
            if name:
                user.full_name = name[:128]
        if not user.contact and payload.get("username"):
            user.contact = f"@{payload['username']}"[:256]
        user.save()
        text = "Готово. Откройте сайт, чтобы войти."
    elif account:
        auth_code.user = account
        text = "Готово. Откройте сайт, чтобы войти."
    else:
        text = "Telegram подтверждён. На сайте останется короткая анкета."

    auth_code.telegram_data = payload
    auth_code.save()
    url = f"{settings.APP_HOST}{reverse('telegram_continue')}?code={auth_code.code}"
    return text, url


def finish(request):
    code = (request.GET.get("code") or "").strip().upper()
    auth_code = Code.objects.filter(code=code).select_related("user").first()
    payload = auth_code.telegram_data if auth_code and isinstance(auth_code.telegram_data, dict) else {}
    telegram_id = str(payload.get("id") or "")
    if not auth_code or auth_code.is_expired() or not telegram_id.isdigit():
        return render(request, "error.html", {
            "title": "Ссылка не сработала",
            "message": "Сначала нажмите кнопку в боте, потом откройте ссылку, которую он пришлёт.",
        })

    account = User.objects.filter(telegram_id=telegram_id).first()
    if auth_code.user_id:
        if not account or account.pk != auth_code.user_id:
            return render(request, "error.html", {
                "title": "Ссылка не сработала",
                "message": "Откройте бота ещё раз со страницы входа. Эта ссылка уже не действует.",
            })
        auth_code.delete()
        return account

    if account:
        auth_code.delete()
        return account

    form = TelegramSignupForm(request.POST or None, telegram_data=payload)
    if request.method == "GET" or not form.is_valid():
        return render(request, "authn/signup.html", {"code": code, "form": form})

    with transaction.atomic():
        auth_code = Code.objects.select_for_update(of=("self",)).filter(pk=auth_code.pk).first()
        if not auth_code or auth_code.user_id or str((auth_code.telegram_data or {}).get("id") or "") != telegram_id:
            return render(request, "error.html", {
                "title": "Ссылка не сработала",
                "message": "Откройте бота ещё раз со страницы входа. Эта ссылка уже не действует.",
            })
        if User.objects.filter(telegram_id=telegram_id).exists():
            return render(request, "error.html", {
                "title": "Ссылка не сработала",
                "message": "Откройте бота ещё раз со страницы входа. Эта ссылка уже не действует.",
            })

        base = (slugify(form.cleaned_data["full_name"]) or "user")[:24]
        if base == "me":
            base = "user"
        slug = base
        number = 2
        while User.objects.filter(slug=slug).exists():
            suffix = f"-{number}"
            slug = f"{base[:32 - len(suffix)]}{suffix}"
            number += 1

        user = User.objects.create_user(
            username=slug,
            email=form.cleaned_data["email"],
            full_name=form.cleaned_data["full_name"],
            city=form.cleaned_data["city"],
            country=form.cleaned_data["country"],
            contact=form.cleaned_data["contact"],
            avatar=form.cleaned_data["avatar"] or None,
        )
        user.telegram_id = telegram_id
        user.telegram_data = auth_code.telegram_data
        user.save()
        auth_code.delete()
    user.just_created = True
    return user
