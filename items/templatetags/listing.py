from urllib.parse import urlencode

from django import template
from django.urls import reverse

from common.templatetags.islands import island

register = template.Library()


def feed_querystring(request):
    params = {}
    sort = request.GET.get("sort")
    if sort in {"date", "rating"}:
        params["sort"] = sort
    hide = (request.GET.get("hide_global") or "").lower()
    if hide in {"1", "true", "on", "yes"}:
        params["hide_global"] = "1"
    return urlencode(params)


@register.simple_tag(takes_context=True)
def listing_url(context, country="", city="", category="", subcategory=""):
    request = context["request"]
    country = country or request.country_id
    city = city or request.city_id

    if country == "everywhere" and city == "everywhere" and not category:
        path = "/"
    else:
        path = f"/{country}/{city}/"
        if category:
            path += f"{category}/"
            if subcategory:
                path += f"{subcategory}/"

    query = feed_querystring(request)
    return f"{path}?{query}" if query else path



@register.simple_tag
def item_url(item):
    return item.get_absolute_url()


@register.simple_tag(takes_context=True)
def item_upvote(context, item, voted_items=None):
    """{% item_upvote item voted_items %} where voted_items is a set of item ids voted by the current user"""
    user = context["request"].user
    is_own = user.is_authenticated and user.pk == item.author_id
    return island(
        "UpvoteButton",
        upvotes=item.upvotes,
        voted=item.id in (voted_items or ()),
        upvote_url=reverse("item_upvote", args=[item.id]),
        retract_url=reverse("item_retract_vote", args=[item.id]),
        login_url=None if user.is_authenticated else reverse("login"),
        disabled=is_own or item.visibility == item.VISIBILITY_DRAFT,
    )
