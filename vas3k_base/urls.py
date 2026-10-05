from django.conf import settings
from django.urls import include, path

from authn.views import banned, bot_page, club_callback, log_in, log_out, login_club, login_telegram, telegram_continue
from bookmarks.api import toggle_item_bookmark
from complaints.api import flag_item
from bookmarks.views import bookmarks_page, remove_bookmark
from comments.api import retract_comment_vote, upvote_comment
from godmode.views.main import (
    godmode,
    godmode_action,
    godmode_create_model,
    godmode_delete_model,
    godmode_edit_model,
    godmode_list_model,
    godmode_show_page,
)
from comments.views import create_comment, delete_comment, edit_comment
from common.api import upload_image
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
from counters.views import user_ratings
from notifications.views import remove_subscription, toggle_listing_subscription
from users.api import update_user_flag
from users.views import edit_profile, profile_page, welcome

urlpatterns = [
    path("", index_page, name="index"),

    path("login/", log_in, name="login"),
    path("logout/", log_out, name="logout"),
    path("welcome/", welcome, name="welcome"),
    path("bot/", bot_page, name="bot"),
    path("banned/", banned, name="banned"),

    path("auth/login/club/", login_club, name="login_club"),
    path("auth/club_callback/", club_callback, name="club_callback"),
    path("auth/login/telegram/", login_telegram, name="login_telegram"),
    path("auth/telegram/", telegram_continue, name="telegram_continue"),

    path("user/<slug:slug>/edit/", edit_profile, name="user_profile_edit"),
    path("user/<slug:slug>/ratings/", user_ratings, name="user_ratings"),
    path("user/<slug:slug>/", profile_page, name="user_profile"),
 
    path("bookmarks/", bookmarks_page, name="bookmarks"),
    path("bookmarks/subscriptions/<uuid:subscription_id>/remove/", remove_subscription, name="subscription_remove"),
    path("bookmarks/<uuid:item_id>/remove/", remove_bookmark, name="bookmark_remove"),
 
    path("items/new/", create_item, name="item_create"),
    path("items/<uuid:item_id>/edit/", edit_item, name="item_edit"),
    path("items/<uuid:item_id>/hide/", hide_item, name="item_hide"),
    path("items/<uuid:item_id>/delete/", delete_item, name="item_delete"),
    path("items/<uuid:item_id>/comments/", create_comment, name="item_comment"),
    path("comments/<uuid:comment_id>/edit/", edit_comment, name="comment_edit"),
    path("comments/<uuid:comment_id>/delete/", delete_comment, name="comment_delete"),

    path("api/subscriptions/toggle/", toggle_listing_subscription, name="subscription_toggle"),
    path("api/items/<uuid:item_id>/upvote/", upvote_item, name="item_upvote"),
    path("api/items/<uuid:item_id>/bookmark/", toggle_item_bookmark, name="item_bookmark"),
    path("api/items/<uuid:item_id>/flag/", flag_item, name="item_flag"),
    path("api/items/<uuid:item_id>/retract_vote/", retract_item_vote, name="item_retract_vote"),
    path("api/comments/<uuid:comment_id>/upvote/", upvote_comment, name="comment_upvote"),
    path("api/comments/<uuid:comment_id>/retract_vote/", retract_comment_vote, name="comment_retract_vote"),
    path("api/images/", upload_image, name="image_upload"),
    path("api/me/flags/", update_user_flag, name="user_flag"),

    path("godmode/", godmode, name="godmode"),
    path("godmode/page/<slug:page_name>/", godmode_show_page, name="godmode_show_page"),
    path("godmode/<slug:model_name>/", godmode_list_model, name="godmode_list_model"),
    path("godmode/<slug:model_name>/create/", godmode_create_model, name="godmode_create_model"),
    path("godmode/<slug:model_name>/<str:item_id>/edit/", godmode_edit_model, name="godmode_edit_model"),
    path("godmode/<slug:model_name>/<str:item_id>/delete/", godmode_delete_model, name="godmode_delete_model"),
    path("godmode/<slug:model_name>/<str:item_id>/action/<str:action_code>/", godmode_action, name="godmode_action"),

    path("<str:country>/", index_page, name="country_index"),
    path("<str:country>/<str:city>/", listing_page, name="listing"),
    path("<str:country>/<str:city>/<slug:category>/", listing_page, name="listing_category"),
    path("<str:country>/<str:city>/<slug:category>/<uuid:item_id>/", item_page, name="item_without_subcategory"),
    path("<str:country>/<str:city>/<slug:category>/<slug:subcategory>/", listing_page, name="listing_subcategory"),
    path("<str:country>/<str:city>/<slug:category>/<slug:subcategory>/<uuid:item_id>/", item_page, name="item"),
]

if settings.DEBUG:
    urlpatterns = [
        path("__debug__/", include("debug_toolbar.urls")),
        *urlpatterns,
    ]
