from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from comments.forms import CommentForm
from comments.models import Comment, CommentVote
from common.request import parse_ip_address, parse_useragent
from items.models import Item, ItemVote


def _back_to_item(item):
    return redirect(item.get_absolute_url() or "index")


@login_required
@require_POST
def upvote_item(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    ItemVote.upvote(request.user, item, request)
    return _back_to_item(item)


@login_required
@require_POST
def create_comment(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    form = CommentForm(request.POST, item=item)
    if not form.is_valid():
        messages.error(request, " ".join(error for errors in form.errors.values() for error in errors))
        return _back_to_item(item)

    Comment.objects.create(
        author=request.user,
        item=item,
        reply_to=form.cleaned_data["reply_to"],
        text=form.cleaned_data["text"],
        ipaddress=parse_ip_address(request),
        useragent=parse_useragent(request),
    )
    return _back_to_item(item)


@login_required
@require_POST
def upvote_comment(request, comment_id):
    comment = get_object_or_404(Comment.objects.select_related("item", "author"), pk=comment_id, deleted_at__isnull=True)
    if not comment.item_id:
        raise Http404()
    CommentVote.upvote(request.user, comment, request)
    return _back_to_item(comment.item)
