from bookmarks.models import Bookmark
from complaints.models import Flag
from categories.models import Category
from comments.models import Comment
from geo.models import GeoCity, GeoCountry
from godmode.actions.item_view import view_item_action
from godmode.actions.user_ban import get_ban_action, post_ban_action
from godmode.actions.user_profile import view_profile_action
from godmode.admin import ClubAdmin, ClubAdminAction, ClubAdminField, ClubAdminGroup, ClubAdminModel
from items.models import Item
from notifications.models import Subscription
from users.models import User

ADMIN = ClubAdmin(
    title="Админка Базы",
    groups=[
        ClubAdminGroup(
            title="Люди",
            icon="🪪",
            models=[
                ClubAdminModel(
                    model=User,
                    title="Пользователи",
                    icon="👤",
                    name="users",
                    title_field="full_name",
                    allow_delete=False,
                    list_fields=[
                        ClubAdminField(
                            name="avatar",
                            display_name="🖼️",
                            list_template="godmode/widgets/avatar.html",
                        ),
                        "full_name",
                        "slug",
                        "email",
                        "city",
                        "country",
                        "is_staff",
                        "is_superuser",
                        "roles",
                        "upvotes",
                        "created_at",
                        "last_activity_at",
                        "is_banned_until",
                        "deleted_at",
                    ],
                    hide_fields=["password"],
                    actions={
                        "profile": ClubAdminAction(
                            title="🪪 Профиль",
                            get=view_profile_action,
                        ),
                        "ban": ClubAdminAction(
                            title="💣 Забанить",
                            get=get_ban_action,
                            post=post_ban_action,
                        ),
                    },
                ),
            ],
        ),
        ClubAdminGroup(
            title="Посты",
            icon="✏️",
            models=[
                ClubAdminModel(
                    model=Item,
                    title="Посты",
                    icon="📝",
                    name="items",
                    title_field="title",
                    list_fields=[
                        "title",
                        "author",
                        "category",
                        "subcategory",
                        "country",
                        "city",
                        "visibility",
                        "upvotes",
                        "comment_count",
                        "bookmark_count",
                        "published_at",
                        "expires_at",
                        "deleted_at",
                    ],
                    hide_fields=["description", "images", "contacts"],
                    actions={
                        "open": ClubAdminAction(
                            title="📝 Открыть",
                            get=view_item_action,
                        ),
                        "ban": ClubAdminAction(
                            title="💣 Забанить автора",
                            get=get_ban_action,
                            post=post_ban_action,
                        ),
                    },
                ),
                ClubAdminModel(
                    model=Comment,
                    title="Комментарии",
                    icon="💭",
                    name="comments",
                    list_fields=[
                        "item",
                        "author",
                        "text",
                        "vibe",
                        "upvotes",
                        "created_at",
                        "deleted_at",
                    ],
                ),
                ClubAdminModel(
                    model=Bookmark,
                    title="Закладки",
                    icon="💙",
                    name="bookmarks",
                    list_fields=[
                        "user",
                        "item",
                        "created_at",
                    ],
                ),
                ClubAdminModel(
                    model=Flag,
                    title="Жалобы",
                    icon="🚩",
                    name="flags",
                    list_fields=[
                        "item",
                        "user",
                        "reason",
                        "comment",
                        "created_at",
                        "updated_at",
                    ],
                ),
            ],
        ),
        ClubAdminGroup(
            title="Каталог",
            icon="🗂️",
            models=[
                ClubAdminModel(
                    model=Category,
                    title="Категории",
                    icon="🏷️",
                    name="categories",
                    title_field="name",
                    list_fields=[
                        "icon",
                        "name",
                        "id",
                        "parent",
                        "is_global",
                        "sort_order",
                    ],
                ),
                ClubAdminModel(
                    model=GeoCountry,
                    title="Страны",
                    icon="🌍",
                    name="countries",
                    title_field="name",
                    list_fields=[
                        "icon",
                        "name",
                        "id",
                        "items_count",
                        "sort_order",
                    ],
                ),
                ClubAdminModel(
                    model=GeoCity,
                    title="Города",
                    icon="🏙️",
                    name="cities",
                    title_field="name",
                    list_fields=[
                        "icon",
                        "name",
                        "id",
                        "country",
                        "items_count",
                        "sort_order",
                    ],
                ),
            ],
        ),
        ClubAdminGroup(
            title="Уведомления",
            icon="🔔",
            models=[
                ClubAdminModel(
                    model=Subscription,
                    title="Подписки",
                    icon="📬",
                    name="subscriptions",
                    list_fields=[
                        "user",
                        "country",
                        "city",
                        "category",
                        "query",
                        "created_at",
                    ],
                ),
            ],
        ),
    ],
    foreign_key_templates={
        User: "godmode/widgets/user.html",
        Item: "godmode/widgets/item.html",
        Comment: "godmode/widgets/comment.html",
        Category: "godmode/widgets/category.html",
        GeoCountry: "godmode/widgets/geo.html",
        GeoCity: "godmode/widgets/geo.html",
    },
)

ITEMS_PER_PAGE = 100
