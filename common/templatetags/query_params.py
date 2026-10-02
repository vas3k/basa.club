from copy import deepcopy

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def append_query_param(context, **kwargs):
    query_params = deepcopy(context.request.GET)
    for param, value in kwargs.items():
        query_params[param] = value
    return "?" + query_params.urlencode()


@register.simple_tag(takes_context=True)
def paginator_page_url(context, number):
    query_params = deepcopy(context.request.GET)
    query_params[context.get("page_param") or "page"] = number
    return "?" + query_params.urlencode()
