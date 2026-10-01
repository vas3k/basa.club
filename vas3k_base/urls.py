from django.urls import path

from authn.views import bot_page, club_callback, log_in, log_out, login_club, login_telegram, telegram_continue
from comments.api import retract_comment_vote, upvote_comment
from comments.views import create_comment, delete_comment
from items.api import retract_item_vote, upvote_item
from items.views import (
    create_item,
    delete_item,
    edit_item,
    hide_item,
    index_page,
    item_page,
    listing_page,
)
from users.views import edit_profile, profile_page

urlpatterns = [
    path("", index_page, name="index"),
    path("login/", log_in, name="login"),
    path("logout/", log_out, name="logout"),
    path("bot/", bot_page, name="bot"),
    path("auth/login/club/", login_club, name="login_club"),
    path("auth/club_callback/", club_callback, name="club_callback"),
    path("auth/login/telegram/", login_telegram, name="login_telegram"),
    path("auth/telegram/", telegram_continue, name="telegram_continue"),
    path("user/<slug:slug>/edit/", edit_profile, name="user_profile_edit"),
    path("user/<slug:slug>/", profile_page, name="user_profile"),
    path("items/new/", create_item, name="item_create"),
    path("items/<uuid:item_id>/edit/", edit_item, name="item_edit"),
    path("items/<uuid:item_id>/hide/", hide_item, name="item_hide"),
    path("items/<uuid:item_id>/delete/", delete_item, name="item_delete"),
    path("items/<uuid:item_id>/comments/", create_comment, name="item_comment"),
    path("comments/<uuid:comment_id>/delete/", delete_comment, name="comment_delete"),

    path("api/items/<uuid:item_id>/upvote/", upvote_item, name="item_upvote"),
    path("api/items/<uuid:item_id>/retract_vote/", retract_item_vote, name="item_retract_vote"),
    path("api/comments/<uuid:comment_id>/upvote/", upvote_comment, name="comment_upvote"),
    path("api/comments/<uuid:comment_id>/retract_vote/", retract_comment_vote, name="comment_retract_vote"),

    path("<str:country>/<str:city>/", listing_page, name="listing"),
    path("<str:country>/<str:city>/<slug:category>/", listing_page, name="listing_category"),
    path("<str:country>/<str:city>/<slug:category>/<slug:subcategory>/", listing_page, name="listing_subcategory"),
    path("<str:country>/<str:city>/<slug:category>/<slug:subcategory>/<uuid:item_id>/", item_page, name="item"),
]
