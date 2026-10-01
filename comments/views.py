from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from comments.forms import CommentForm, ReplyForm
from comments.models import Comment
from items.models import Item
from items.views import render_item_page


@login_required
@require_POST
def create_comment(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    is_reply = bool(request.POST.get("reply_to"))
    form = ReplyForm(request.POST, item=item) if is_reply else CommentForm(request.POST, item=item)

    if form.is_valid():
        comment = form.save(author=request.user, request=request)
        return redirect(f"{item.get_absolute_url()}#comment-{comment.id}")

    return render_item_page(
        request,
        item,
        comment_form=None if is_reply else form,
        reply_form=form if is_reply else None,
        status=400,
    )


@login_required
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(
        Comment.objects.select_related("item", "author"),
        pk=comment_id,
        deleted_at__isnull=True,
    )
    if comment.author_id != request.user.pk:
        raise Http404()
    comment.soft_delete(by_user=request.user)
    url = comment.item.get_absolute_url()
    if comment.reply_to_id:
        return redirect(f"{url}#comment-{comment.reply_to_id}")
    return redirect(f"{url}#comments")
