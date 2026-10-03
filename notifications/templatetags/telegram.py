from django import template
from django.template.defaultfilters import truncatechars_html
from django.utils.safestring import mark_safe

from common.markdown.markdown import markdown_tg

register = template.Library()


@register.simple_tag
def render_tg(text, truncate=None):
    result = mark_safe(markdown_tg(text or ""))
    if truncate:
        desired_length = int(truncate)
        limit = desired_length
        for _attempt in range(30):
            if len(result) <= desired_length:
                break
            result = truncatechars_html(result, limit)
            limit -= 100
            if limit < 1:
                break

    if "\n" in result:
        result = mark_safe("\n" + result)
    return result
