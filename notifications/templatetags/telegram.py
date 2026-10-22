from django import template
from django.utils.safestring import mark_safe

from common.markdown.markdown import markdown_tg
from django.template.defaultfilters import truncatechars_html

register = template.Library()


@register.simple_tag
def render_tg(text, truncate=None):
    result = markdown_tg(text or "")
    if truncate is not None:
        result = truncatechars_html(result, truncate)
    if "\n" in result:
        result = "\n" + result
    return mark_safe(result)
