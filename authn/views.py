import logging
from uuid import UUID

import requests
from authlib.integrations.base_client import OAuthError
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from authn.helpers import start_session
from authn.models import Code
from authn.providers import club, telegram
from notifications import notification
from authn.providers.club import oauth
from users.models import User
from items.models import Item
from vas3k_base.exceptions import RateLimitException

log = logging.getLogger(__name__)


def log_in(request):
    try:
        next_item_id = str(UUID(request.GET.get("next_item_id", "")))
    except ValueError:
        next_item_id = None
    if next_item_id:
        request.session["next_item_id"] = next_item_id
    else:
        request.session.pop("next_item_id", None)

    if request.user.is_authenticated:
        request.session.pop("next_item_id", None)
        if next_item_id:
            item = Item.objects.filter(id=next_item_id).first()
            if item:
                return redirect(item.get_absolute_url())
        return redirect("user_profile", slug=request.user.slug)

    return render(request, "users/login.html")


def banned(request):
    if not request.user.is_authenticated or not request.user.is_banned:
        return redirect("index")
    left = request.user.is_banned_until - timezone.now()
    return render(request, "banned.html", {
        "is_permanent": request.user.is_permanently_banned,
        "days": left.days,
        "hours": left.seconds // 3600,
        "minutes": (left.seconds % 3600) // 60,
    }, status=403)


@require_POST
def log_out(request):
    logout(request)
    response = redirect("index")
    response.delete_cookie("token", path="/")
    return response


def login_club(request):
    redirect_uri = f"https://{request.get_host()}{reverse('club_callback')}"
    return oauth.club.authorize_redirect(
        request=request,
        redirect_uri=redirect_uri,
        scope=["openid", "contact"]
    )


def club_callback(request):
    try:
        token = oauth.club.authorize_access_token(request)
    except OAuthError as ex:
        log.warning("Club OAuth rejected: %s", ex.error)
        return render(request, "error.html", {
            "title": "Ошибка OAuth",
            "message": "Не удалось подтвердить вход через Клуб. Попробуйте войти ещё раз."
        })
    except requests.exceptions.RequestException as ex:
        log.error("Club token request failed: %s", type(ex).__name__)
        return render(request, "error.html", {
            "title": "Ошибка Клуба",
            "message": "Что-то сломалось или сайт упал, попробуйте еще раз."
        })

    userinfo = (token or {}).get("userinfo")

    if not userinfo:
        return render(request, "error.html", {
            "title": "Что-то пошло не так",
            "message": "При авторизации потерялся токен юзера. Попробуйте войти еще раз."
        })

    user_slug = userinfo["sub"]
    try:
        profile_response = requests.get(
            url=f"{oauth.club.api_base_url}/user/me.json",
            headers={"Authorization": f"{token['token_type']} {token['access_token']}"},
            timeout=30,
        )
        profile_response.raise_for_status()
        club_profile = profile_response.json()
    except (requests.exceptions.RequestException, ValueError) as ex:
        log.error("Club profile request failed: %s", type(ex).__name__)
        club_profile = {}

    member = club_profile.get("user")
    if not member:
        return render(request, "error.html", {
            "message": format_html("Член Клуба с именем {} не найден. "
                       "<a href=\"https://vas3k.club\">Попробуйте</a> войти в свой "
                       "аккаунт и потом авторизоваться здесь снова.", user_slug)
        })

    if member["slug"] != user_slug:
        log.error("Club OAuth subject does not match the profile")
        return render(request, "error.html", {"message": "Клуб вернул другой профиль. Повторите вход."}, status=403)

    if member.get("payment_status") != "active":
        return render(request, "error.html", {
            "message": format_html("{} <a href=\"https://vas3k.club\">Продлите</a> её здесь.",
                                   "Ваша подписка на Клуб истекла.")
        })

    telegram_data = member.get("telegram") or {}
    telegram_id = str(telegram_data["id"]) if telegram_data.get("id") else None

    club_user = User.all_objects.filter(club_slug=user_slug).first()
    telegram_user = User.all_objects.filter(telegram_id=telegram_id).first() if telegram_id else None
    if club_user and telegram_user and club_user.id != telegram_user.id:
        log.warning("Club/Telegram identity conflict users=%s,%s", club_user.id, telegram_user.id)
        return render(request, "error.html", {
            "message": "Клуб и Telegram уже связаны с разными профилями. Обратитесь к модераторам для объединения.",
        })
    user = telegram_user or club_user
    if user and (user.deleted_at or user.is_banned):
        return render(request, "error.html", {"message": "Аккаунт заблокирован."}, status=403)
    if user and (
        (user.club_slug and user.club_slug != user_slug)
        or (user.telegram_id and telegram_id and user.telegram_id != telegram_id)
    ):
        return render(request, "error.html", {
            "message": "В профиле привязан другой Клуб или Telegram. Обратитесь к модераторам.",
        })
    if not telegram_id and not user:
        return render(request, "error.html", {
            "message": "Сначала привяжите Telegram в профиле Клуба, затем повторите вход в Базу.",
        })

    created = user is None
    email = userinfo.get("email") or member.get("email")
    if not email or User.all_objects.filter(email__iexact=email).exclude(id=user.id if user else None).exists():
        return render(request, "error.html", {
            "message": "Почта Клуба отсутствует или занята другим профилем. Проверьте Telegram в Клубе или обратитесь к модераторам.",
        })
    if created:
        slug = user_slug[:32]
        if User.all_objects.filter(slug=slug).exists() or slug == "me":
            slug = f"tg-{telegram_id}"
        user = User.objects.create_user(username=slug, email=email, telegram_id=telegram_id)
    fill_bio = not user.bio
    user.email = email
    if telegram_id:
        user.telegram_id = telegram_id
        user.telegram_data = telegram_data
    club.apply_club_profile(user, member, fill_bio=fill_bio)
    user.save()

    log.info("Club login completed user=%s created=%s", user.id, created)
    return start_session(request, user, new_user=created)


@require_POST
def login_telegram(request):
    if request.user.is_authenticated:
        return redirect("user_profile", slug=request.user.slug)
    try:
        if settings.DEBUG:
            payload = {
                "id": "9007199254740992",
                "first_name": "Local",
                "last_name": "Developer",
                "debug": True,
            }
            account = User.all_objects.filter(telegram_id=payload["id"]).first()
            if account and not (account.telegram_data or {}).get("debug"):
                return render(request, "error.html", {"message": "Тестовый Telegram ID уже занят другим аккаунтом."})
            auth_code = Code.create_for_user(user=None, recipient="local-telegram-development")
            payload["next_item_id"] = request.session.get("next_item_id")
            auth_code.telegram_data = payload
            auth_code.save(update_fields=["telegram_data"])
            return redirect(f"{reverse('telegram_continue')}?code={auth_code.code}")
        return redirect(telegram.bot_url(request))
    except RateLimitException as ex:
        return render(request, "error.html", {"title": ex.title, "message": ex.message})


@login_required
@require_http_methods(["GET", "POST"])
def bot_page(request):
    if request.method != "POST":
        return render(request, "authn/bot.html")

    try:
        url = telegram.bot_url(request, user=request.user)
    except RateLimitException as ex:
        return render(request, "error.html", {"title": ex.title, "message": ex.message})

    return redirect(url)


@never_cache
@require_http_methods(["GET", "POST"])
def telegram_continue(request):
    user = telegram.finish(request)
    if not isinstance(user, User):
        user["Referrer-Policy"] = "no-referrer"
        return user

    response = start_session(request, user, new_user=getattr(user, "just_created", False))
    response["Referrer-Policy"] = "no-referrer"
    if not user.is_banned and not (user.telegram_data or {}).get("debug"):
        notification.user_logged_in(user)
    return response

