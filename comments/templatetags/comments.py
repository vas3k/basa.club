from django import template
from django.urls import reverse

from common.templatetags.islands import island

register = template.Library()


@register.simple_tag(takes_context=True)
def comment_upvote(context, comment, voted_comments=None, variant="inline"):
    """{% comment_upvote comment voted_comments %} where voted_comments is a set of comment ids voted by the current user"""
    user = context["request"].user
    return island(
        "UpvoteButton",
        upvotes=comment.upvotes,
        voted=comment.id in (voted_comments or ()),
        upvote_url=reverse("comment_upvote", args=[comment.id]),
        retract_url=reverse("comment_retract_vote", args=[comment.id]),
        login_url=None if user.is_authenticated else reverse("login"),
        disabled=user.is_authenticated and user.pk == comment.author_id,
        variant=variant,
        label="Полезно!" if variant == "inline" else None,
    )
