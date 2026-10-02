from django import template
from django.urls import reverse

from common.templatetags.islands import island

register = template.Library()


@register.simple_tag(takes_context=True)
def item_bookmark(context, item):
    user = context["request"].user
    return island(
        "BookmarkButton",
        bookmark_count=item.bookmark_count,
        bookmark_url=reverse("item_bookmark", args=[item.id]),
        login_url=None if user.is_authenticated else reverse("login"),
    )
