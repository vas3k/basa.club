from django import template
from django.urls import reverse

from common.templatetags.islands import island
from complaints.models import Flag

register = template.Library()


@register.simple_tag(takes_context=True)
def item_flag(context, item):
    user = context["request"].user
    return island(
        "FlagButton",
        flag_url=reverse("item_flag", args=[item.id]),
        login_url=None if user.is_authenticated else reverse("login"),
        comment_max_length=Flag.COMMENT_MAX_LENGTH,
        reasons=[{"value": value, "label": label} for value, label in Flag.REASONS],
    )
