from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from comments.forms import CommentForm, ReplyForm
from comments.models import Comment
from common import counters
from items.models import Item
from items.views import render_item_page


@login_required
@require_POST
def create_comment(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    is_reply = bool(request.POST.get("reply_to"))
    form = ReplyForm(request.POST, item=item) if is_reply else CommentForm(request.POST, item=item)

    if form.is_valid():
        comment = form.save(author=request.user, request=request, commit=False)
        comment.save()
        counters.comment_created(comment)
        return redirect(f"{item.get_absolute_url()}#comment-{comment.id}")

    return render_item_page(
        request,
        item,
        comment_form=None if is_reply else form,
        reply_form=form if is_reply else None,
        status=400,
    )


@login_required
@require_http_methods(["GET", "POST"])
def edit_comment(request, comment_id):
    comment = get_object_or_404(
        Comment.objects.select_related("item", "author", "reply_to"),
        pk=comment_id,
    )
    if comment.author_id != request.user.pk:
        raise Http404()

    is_reply = bool(comment.reply_to_id)
    form_class = ReplyForm if is_reply else CommentForm
    form = form_class(request.POST or None, item=comment.item, instance=comment)
    form.fields.pop("vibe", None)
    if is_reply:
        form.fields["text"].widget = CommentForm.Meta.widgets["text"]

    if request.method == "POST" and form.is_valid():
        comment = form.save(author=request.user, request=request, commit=False)
        comment.save()
        return redirect(f"{comment.item.get_absolute_url()}#comment-{comment.id}")

    return render(request, "comments/edit.html", {
        "comment": comment,
        "item": comment.item,
        "form": form,
        "is_reply": is_reply,
        "form_title": "Редактировать ответ" if is_reply else "Редактировать комментарий",
    })


@login_required
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(
        Comment.objects.select_related("item", "author"),
        pk=comment_id,
    )
    if comment.author_id != request.user.pk:
        raise Http404()

    comment.delete(by=request.user)
    counters.comment_deleted(comment)

    url = comment.item.get_absolute_url()
    if comment.reply_to_id:
        return redirect(f"{url}#comment-{comment.reply_to_id}")
    return redirect(f"{url}#comments")
