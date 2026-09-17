from django.urls import path

from authn.views import club_callback, log_in, log_out, login_club
from items.views import index_page, item_page, listing_page

urlpatterns = [
    path("", index_page, name="index"),
    path("login/", log_in, name="login"),
    path("logout/", log_out, name="logout"),
    path("auth/login/club/", login_club, name="login_club"),
    path("auth/club_callback/", club_callback, name="club_callback"),

    path("<str:country>/<str:city>/", listing_page, name="listing"),
    path("<str:country>/<str:city>/<slug:category>/", listing_page, name="listing_category"),
    path("<str:country>/<str:city>/<slug:category>/<slug:subcategory>/", listing_page, name="listing_subcategory"),
    path("<str:country>/<str:city>/<slug:category>/<slug:subcategory>/<uuid:item_id>/", item_page, name="item"),
]
