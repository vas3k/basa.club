from django import template
from django.urls import reverse

from common.templatetags.islands import island

register = template.Library()


@register.simple_tag(takes_context=True)
def comment_upvote(context, comment, variant="inline"):
    """{% comment_upvote comment %} — comment.upvoted_at comes from Comment.objects_for_user"""
    user = context["request"].user
    return island(
        "UpvoteButton",
        upvotes=comment.upvotes,
        voted=bool(getattr(comment, "upvoted_at", None)),
        upvote_url=reverse("comment_upvote", args=[comment.id]),
        retract_url=reverse("comment_retract_vote", args=[comment.id]),
        login_url=None if user.is_authenticated else reverse("login"),
        disabled=user.is_authenticated and user.pk == comment.author_id,
        variant=variant,
        label="Полезно:" if variant == "inline" else None,
    )
