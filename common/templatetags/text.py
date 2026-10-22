import html

from django import template
from django.template.defaultfilters import truncatechars
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

from common.markdown.markdown import markdown_text

register = template.Library()

# Public pages and OG tags show this much of an item description. The rest stays behind login.
PUBLIC_PREVIEW_LENGTH = 240


@register.simple_tag
def text_length_class(text, default_class, *length_class_pairs):
    """Usage: {% text_length_class text "title-normal" 50 "title-medium" 100 "title-small" %}"""
    if len(length_class_pairs) % 2:
        raise template.TemplateSyntaxError("text_length_class requires length/class pairs")

    text_length = len(text or "")
    css_class = default_class
    matched_length = -1
    for length, candidate_class in zip(length_class_pairs[::2], length_class_pairs[1::2]):
        length = int(length)
        if matched_length < length <= text_length:
            matched_length = length
            css_class = candidate_class

    return css_class


@register.filter
def markdown(text):
    return mark_safe(markdown_text(text or ""))


@register.filter
def markdown_summary(text):
    """Plain text without markup, use with |truncatechars for previews"""
    plain = strip_tags(markdown_text(text or "", disable_mentions=True))
    return " ".join(html.unescape(plain).split())


@register.filter
def public_preview(text):
    """First PUBLIC_PREVIEW_LENGTH characters of description text, markup stripped."""
    return truncatechars(markdown_summary(text), PUBLIC_PREVIEW_LENGTH)


@register.filter
def public_preview_cut(text):
    return len(markdown_summary(text)) > PUBLIC_PREVIEW_LENGTH


@register.filter
def cool_number(value, num_decimals=1):
    """
    11500 -> 11.5K, etc
    """
    int_value = int(value or 0)
    formatted_number = "{{:.{}f}}".format(num_decimals)
    if int_value < 1000:
        return str(int_value)
    elif int_value < 1000000:
        return formatted_number.format(int_value / 1000.0).rstrip("0").rstrip(".") + "K"
    else:
        return formatted_number.format(int_value / 1000000.0).rstrip("0").rstrip(".") + "M"


@register.filter
def pluralize(value, forms):
    """
    Russian plural forms: "запись,записи,записей".
    1 запись, 2 записи, 5 записей, 11 записей, 21 запись.
    """
    one, few, many = (part.strip() for part in str(forms).split(","))
    number = abs(int(value or 0))
    last_two = number % 100
    last_one = number % 10
    if last_one == 1 and last_two != 11:
        return one
    if last_one in (2, 3, 4) and last_two not in (12, 13, 14):
        return few
    return many


@register.filter
def rating(value):
    """Ratings are stored as integers and shown divided by 10: 15 -> +1.5, -7 -> -0.7"""
    shown = (value or 0) / 10
    if shown > 0:
        return f"+{shown:.1f}"
    return f"{shown:.1f}"
