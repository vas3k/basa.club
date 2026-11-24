import logging

import requests

from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.text import slugify

from authn.forms import TelegramSignupForm
from authn.models import Code
from geo.models import GeoCountry
from notifications.subscriptions import subscribe_to_geo
from common.request import parse_ip_address, parse_useragent
from users.models import User
from utils.strings import random_code

log = logging.getLogger(__name__)


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
    telegram_id = str(data["id"])
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

    account = User.all_objects.filter(telegram_id=telegram_id).first()
    if account and (account.deleted_at or account.is_banned):
        raise TelegramAuthError("Этот аккаунт недоступен. Обратитесь к модераторам.")
    if auth_code.user_id:
        if auth_code.user.deleted_at or auth_code.user.is_banned:
            raise TelegramAuthError("Этот аккаунт недоступен.")
        if auth_code.user.telegram_id and auth_code.user.telegram_id != telegram_id:
            raise TelegramAuthError("В профиле уже привязан другой Telegram. Обратитесь к модераторам.")
        if account and account.id != auth_code.user_id:
            raise TelegramAuthError("Этот Telegram уже привязан к другому профилю.")
        text = "Бот узнал вас. Нажмите кнопку ниже, чтобы войти."
    elif account:
        auth_code.user = account
        text = "Бот узнал вас. Нажмите кнопку ниже, чтобы войти."
    else:
        text = "Telegram подтверждён. На сайте останется короткая анкета."

    auth_code.code = random_code(settings.AUTH_CODE_LENGTH)
    auth_code.telegram_data = payload
    auth_code.save()
    url = f"{settings.APP_HOST}{reverse('telegram_continue')}?code={auth_code.code}"
    return text, url


def finish(request):
    code = (request.GET.get("code") or "").strip().upper()
    auth_code = Code.objects.filter(code=code).select_related("user").first()
    payload = (auth_code.telegram_data or {}) if auth_code else {}
    telegram_id = str(payload.get("id") or "")
    if payload.get("debug") and not settings.DEBUG:
        return render(request, "error.html", {"message": "Тестовый вход отключён."}, status=403)
    if not auth_code or auth_code.is_expired() or not telegram_id.isdigit():
        return render(request, "error.html", {
            "title": "Ссылка не сработала",
            "message": "Сначала нажмите кнопку в боте, потом откройте ссылку, которую он пришлёт.",
        })

    account = User.all_objects.filter(telegram_id=telegram_id).first()
    if account and (account.deleted_at or account.is_banned):
        return render(request, "error.html", {"message": "Этот аккаунт недоступен."}, status=403)

    if not payload.get("debug"):
        if not settings.CLUB_SERVICE_TOKEN:
            log.error("Telegram login Club lookup is unavailable: CLUB_SERVICE_TOKEN is missing")
            return render(request, "error.html", {
                "message": "Проверка профиля Клуба временно недоступна. Попробуйте позже.",
            }, status=503)
        try:
            response = requests.get(
                f"{settings.CLUB_BASE_URL}/user/by_telegram_id/{telegram_id}.json",
                headers={"X-Service-Token": settings.CLUB_SERVICE_TOKEN},
                timeout=10,
            )
            if response.status_code != 404:
                response.raise_for_status()
                club_slug = response.json()["user"]["slug"]
                log.info("Telegram login redirected to Club OAuth club_slug=%s", club_slug)
                auth_code.delete()
                return redirect("login_club")
        except (requests.exceptions.RequestException, ValueError, KeyError, TypeError) as ex:
            log.error("Telegram login Club lookup failed: %s", type(ex).__name__)
            return render(request, "error.html", {
                "message": "Не удалось проверить профиль Клуба. Попробуйте ещё раз чуть позже.",
            }, status=503)

    if account and account.club_slug and not payload.get("debug"):
        auth_code.delete()
        return redirect("login_club")

    if auth_code.user_id and not auth_code.user.telegram_id:
        if not request.user.is_authenticated or request.user.id != auth_code.user_id:
            return render(request, "error.html", {
                "message": "Откройте ссылку в браузере, где вы вошли в свой профиль Базы.",
            }, status=403)
        if auth_code.user.deleted_at or auth_code.user.is_banned or account:
            return render(request, "error.html", {"message": "Не удалось привязать Telegram к этому профилю."}, status=403)
        if request.method == "GET":
            return render(request, "authn/telegram_confirm.html", {"account": auth_code.user, "linking": True})
        account = auth_code.user
        account.telegram_id = telegram_id
        account.telegram_data = payload
        account.save(update_fields=["telegram_id", "telegram_data"])
        log.info("Telegram linked to user=%s", account.id)

    if auth_code.user_id and (not account or account.id != auth_code.user_id):
        return render(request, "error.html", {
            "title": "Ссылка не сработала",
            "message": "Откройте бота ещё раз со страницы входа. Эта ссылка уже не действует.",
        })

    if account:
        if request.method == "GET":
            return render(request, "authn/telegram_confirm.html", {"account": account})
        auth_code.delete()
        return account

    form = TelegramSignupForm(request.POST or None, telegram_data=payload)
    if payload.get("debug") and not form.is_bound:
        form.initial.update({
            "email": "developer@example.test",
            "bio": "Это локальный аккаунт разработчика для проверки регистрации, профиля, публикации объявлений и комментариев на тестовой Базе.",
        })
    countries = [
        {
            "id": country.id,
            "name": country.name,
            "icon": country.icon,
            "cities": [{"id": city.id, "name": city.name, "icon": city.icon} for city in country.cities.all()],
        }
        for country in GeoCountry.objects.prefetch_related("cities")
    ]
    context = {
        "code": code,
        "form": form,
        "country_id": form["country"].value() or "",
        "city_id": form["city"].value() or "",
        "countries_options": countries,
    }
    if request.method == "GET" or not form.is_valid():
        return render(request, "authn/signup.html", context)

    base = (slugify(form.cleaned_data["full_name"]) or "user")[:24]
    if base == "me":
        base = "user"
    slug = base
    number = 2
    while User.all_objects.filter(slug=slug).exists():
        suffix = f"-{number}"
        slug = f"{base[:32 - len(suffix)]}{suffix}"
        number += 1

    user = User.objects.create_user(
        username=slug,
        email=form.cleaned_data["email"],
        full_name=form.cleaned_data["full_name"],
        bio=form.cleaned_data["bio"],
        telegram_id=telegram_id,
        telegram_data=auth_code.telegram_data,
        city=form.cleaned_data["city"],
        country=form.cleaned_data["country"],
        avatar=form.cleaned_data["avatar"] or None,
        metadata={"is_onboarded": True},
    )
    subscribe_to_geo(user, form.cleaned_data["country_id"], form.cleaned_data["city_id"])
    auth_code.delete()
    log.info("Telegram signup completed user=%s", user.id)
    user.just_created = True
    return user
