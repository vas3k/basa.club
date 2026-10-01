import html

from django import template
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

from common.markdown.markdown import markdown_text

register = template.Library()


@register.filter
def markdown(text):
    return mark_safe(markdown_text(text or ""))


@register.filter
def markdown_summary(text):
    """Plain text without markup, use with |truncatechars for previews"""
    plain = strip_tags(markdown_text(text or "", disable_mentions=True))
    return " ".join(html.unescape(plain).split())


@register.filter
def rating(value):
    """Ratings are stored as integers and shown divided by 10: 15 -> +1.5, -7 -> -0.7"""
    shown = (value or 0) / 10
    if shown > 0:
        return f"+{shown:.1f}"
    return f"{shown:.1f}"
