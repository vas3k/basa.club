from urllib.parse import urlencode

from django import template
from django.urls import reverse

from common.templatetags.islands import island
from common.templatetags.text import rating

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

    if not category and city == "everywhere":
        path = "/" if country == "everywhere" else f"/{country}/"
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
def item_upvote(context, item):
    """{% item_upvote item %} — item.upvoted_at comes from Item.objects_for_user"""
    user = context["request"].user
    is_own = user.is_authenticated and user.pk == item.author_id
    voted = bool(getattr(item, "upvoted_at", None))
    return island(
        "ItemUpvote",
        rating=rating(item.rating),
        voted=voted,
        upvote_url=reverse("item_upvote", args=[item.id]),
        retract_url=reverse("item_retract_vote", args=[item.id]),
        login_url=None if user.is_authenticated else reverse("login"),
        disabled=(is_own or item.visibility == item.VISIBILITY_DRAFT) and not voted,
    )
