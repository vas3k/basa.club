import json

from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def island(island_name, **props):
    """
    Mounts a React component from frontend/src/islands/<island_name>.tsx
    Prop names are converted to camelCase: upvote_url -> upvoteUrl

    {% island "MarkdownEditor" name="description" value=form.description.value %}
    """
    converted_props = {}
    for key, value in props.items():
        first, *rest = key.split("_")
        converted_props[first + "".join(word.capitalize() for word in rest)] = value

    return format_html(
        '<div data-island="{}" data-props="{}"></div>',
        island_name,
        json.dumps(converted_props, cls=DjangoJSONEncoder),
    )
