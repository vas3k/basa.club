import logging

import requests
from authlib.integrations.base_client import OAuthError
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from requests import HTTPError

from authn.providers import club, telegram
from authn.providers.club import oauth
from users.models import User
from vas3k_base.exceptions import RateLimitException

log = logging.getLogger(__name__)

LOGIN_NEXT_SESSION_KEY = "login_next"


def start_session(request, user, redirect_to):
    login(request, user)
    request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    user.last_activity_at = timezone.now()
    user.save(update_fields=["last_activity_at"])
    return redirect(redirect_to)


def home_for(user):
    if user.telegram_id:
        return reverse("user_profile", kwargs={"slug": "me"})
    return reverse("bot")


def safe_next_url(request, url):
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}):
        return url
    return None


def after_login_url(request, user, next_url=None):
    # users without telegram must go through the bot onboarding first
    next_url = safe_next_url(request, next_url or request.session.pop(LOGIN_NEXT_SESSION_KEY, None))
    if next_url and user.telegram_id:
        return next_url
    return home_for(user)


def log_in(request):
    next_url = safe_next_url(request, request.GET.get("next"))
    if request.user.is_authenticated:
        return redirect(after_login_url(request, request.user, next_url))
    if next_url:
        request.session[LOGIN_NEXT_SESSION_KEY] = next_url
    return render(request, "users/login.html")


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
        return render(request, "error.html", {
            "title": "Ошибка OAuth",
            "message": f"Что-то проебалось при авторизации: {ex}"
        })
    except HTTPError as ex:
        return render(request, "error.html", {
            "title": "Ошибка Клуба",
            "message": f"Что-то сломалось или сайт упал, попробуйте еще раз: {ex}"
        })

    userinfo = token.get("userinfo")

    if not token or not userinfo:
        return render(request, "error.html", {
            "title": "Что-то пошло не так",
            "message": "При авторизации потерялся токен юзера. Попробуйте войти еще раз."
        })

    user_slug = userinfo["sub"]
    try:
        club_profile = requests.get(
            url=f"{oauth.club.api_base_url}/user/me.json",
            headers={"Authorization": f"{token['token_type']} {token['access_token']}"},
        ).json()
    except Exception as ex:
        log.exception(ex)
        club_profile = None

    member = club_profile.get("user") if isinstance(club_profile, dict) else None
    if not isinstance(member, dict):
        return render(request, "error.html", {
            "message": f"Член Клуба с именем {user_slug} не найден. "
                       "<a href=\"https://vas3k.club\">Попробуйте</a> войти в свой "
                       "аккаунт и потом авторизоваться здесь снова."
        })

    if member.get("payment_status") != "active":
        return render(request, "error.html", {
            "message": "Ваша подписка на Клуб истекла. "
                       "<a href=\"https://vas3k.club\">Продлите</a> её здесь."
        })

    user = User.objects.filter(Q(email=userinfo["email"]) | Q(slug=userinfo["sub"])).first()
    if user:
        if not user.email or user.email != userinfo["email"]:
            user.email = userinfo["email"]
        club.apply_club_profile(user, club_profile)
        user.save()
    else:
        user = User.objects.create_user(
            username=userinfo["sub"],
            email=userinfo["email"],
        )
        club.apply_club_profile(user, club_profile)
        user.save()

    return start_session(request, user, after_login_url(request, user, request.GET.get("goto")))


def login_telegram(request):
    try:
        return redirect(telegram.bot_url(request))
    except RateLimitException as ex:
        return render(request, "error.html", {"title": ex.title, "message": ex.message})


@login_required
def bot_page(request):
    if request.user.telegram_id:
        return redirect("user_profile", slug="me")
    try:
        url = telegram.bot_url(request, user=request.user)
    except RateLimitException as ex:
        return render(request, "error.html", {"title": ex.title, "message": ex.message})
    return render(request, "authn/bot.html", {"bot_url": url})


@require_http_methods(["GET", "POST"])
def telegram_continue(request):
    user = telegram.finish(request)
    if not isinstance(user, User):
        return user
    return start_session(request, user, after_login_url(request, user))
