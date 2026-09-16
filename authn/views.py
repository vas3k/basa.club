import logging
from urllib.parse import urlparse

from authlib.integrations.base_client import OAuthError
from django.contrib.auth import logout, login
from django.db.models import Q
from django.shortcuts import render, redirect
from django.urls import reverse
from requests import HTTPError

from authn.providers import club
from authn.providers.club import oauth
from users.models import User

log = logging.getLogger(__name__)


def log_in(request):
    if request.user.is_authenticated:
        return redirect("profile")
    return render(request, "users/login.html")


def log_out(request):
    logout(request)
    return redirect("index")


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
    club_profile = club.parse_membership(token)
    if not club_profile or not club_profile.get("user"):
        return render(request, "error.html", {
            "message": f"Член Клуба с именем {user_slug} не найден. "
                       "<a href=\"https://vas3k.club\">Попробуйте</a> войти в свой "
                       "аккаунт и потом авторизоваться здесь снова."
        })

    if club_profile["user"]["payment_status"] != "active":
        return render(request, "error.html", {
            "message": "Ваша подписка на Клуб истекла. "
                       "<a href=\"https://vas3k.club\">Продлите</a> её здесь."
        })


    user = User.objects.filter(Q(email=userinfo["email"]) | Q(slug=userinfo["sub"])).first()
    telegram_id = club_profile["user"]["telegram"].get("id") if club_profile["user"].get("telegram") else None
    if user:
        user.full_name = club_profile["user"]["full_name"]
        user.avatar = club_profile["user"]["avatar"]
        if not user.email or user.email != userinfo["email"]:
            user.email = userinfo["email"]
        user.telegram_id = telegram_id
        user.profile_cache = club_profile
        user.save()
    else:
        user = User.objects.create_user(
            username=userinfo["sub"],
            email=userinfo["email"],
            full_name=club_profile["user"]["full_name"],
            telegram_id=telegram_id,
            avatar=club_profile["user"]["avatar"],
            profile_cache=club_profile,
        )

    login(request, user)

    goto = request.GET.get("goto")
    if goto and urlparse(goto).netloc == request.get_host():
        redirect_to = goto
    else:
        redirect_to = reverse("profile")

    return redirect(redirect_to)
