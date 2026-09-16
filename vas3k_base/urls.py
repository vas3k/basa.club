from django.urls import path

from authn.views import log_in, log_out, login_club, club_callback
from items.views import index_page

urlpatterns = [
    path("", index_page, name="index"),

    # path(r"me/", profile, name="profile"),
    path(r"login/", log_in, name="login"),
    path(r"logout/", log_out, name="logout"),
    path(r"auth/login/club/", login_club, name="login_club"),
    path(r"auth/club_callback/", club_callback, name="club_callback"),
]
