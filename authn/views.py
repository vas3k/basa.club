import logging

import requests
from authlib.integrations.base_client import OAuthError
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.views.decorators.http import require_http_methods, require_POST
from requests import HTTPError

from authn.helpers import start_session
from authn.providers import club, telegram
from authn.providers.club import oauth
from users.models import User
from vas3k_base.exceptions import RateLimitException

log = logging.getLogger(__name__)


def log_in(request):
    if request.user.is_authenticated:
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
        return render(request, "error.html", {
            "title": "Ошибка OAuth",
            "message": f"Что-то проебалось при авторизации: {ex}"
        })
    except HTTPError:
        return render(request, "error.html", {
            "title": "Ошибка Клуба",
            "message": "Что-то сломалось или сайт упал, попробуйте еще раз."
        })

    userinfo = token.get("userinfo") if isinstance(token, dict) else None

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
            timeout=30,
        ).json()
    except (requests.exceptions.RequestException, ValueError, KeyError):
        log.warning("Could not load the Club profile")
        club_profile = None

    member = club_profile.get("user") if isinstance(club_profile, dict) else None
    if not isinstance(member, dict):
        return render(request, "error.html", {
            "message": format_html("Член Клуба с именем {} не найден. "
                       "<a href=\"https://vas3k.club\">Попробуйте</a> войти в свой "
                       "аккаунт и потом авторизоваться здесь снова.", user_slug)
        })

    if member.get("payment_status") != "active":
        return render(request, "error.html", {
            "message": format_html("{} <a href=\"https://vas3k.club\">Продлите</a> её здесь.",
                                   "Ваша подписка на Клуб истекла.")
        })

    created = False
    user = User.objects.filter(Q(email=userinfo["email"]) | Q(slug=userinfo["sub"])).first()
    if user:
        if not user.email or user.email != userinfo["email"]:
            user.email = userinfo["email"]
        club.apply_club_profile(user, club_profile, club_slug=user_slug)
        user.save()
    else:
        user = User.objects.create_user(
            username=userinfo["sub"],
            email=userinfo["email"],
        )
        club.apply_club_profile(user, club_profile, club_slug=user_slug, fill_bio=True)
        user.save()
        created = True

    return start_session(request, user, new_user=created)


def login_telegram(request):
    return redirect("login")


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


@require_http_methods(["GET", "POST"])
def telegram_continue(request):
    user = telegram.finish(request)
    if not isinstance(user, User):
        return user

    return start_session(request, user, new_user=getattr(user, "just_created", False))
