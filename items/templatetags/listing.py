from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def listing_url(context, country="", city="", category="", subcategory=""):
    request = context["request"]
    country = country or request.country_id
    city = city or request.city_id

    if country == "everywhere" and city == "everywhere" and not category:
        return "/"

    path = f"/{country}/{city}/"
    if category:
        path += f"{category}/"
        if subcategory:
            path += f"{subcategory}/"
    return path
