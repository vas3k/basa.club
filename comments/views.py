from copy import deepcopy

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from comments.forms import CommentForm, ReplyForm
from comments.models import Comment
from counters import counters
from items.models import Item
from items.views import render_item_page
from notifications import notification


@login_required
@require_POST
def create_comment(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    is_reply = bool(request.POST.get("reply_to"))
    form = ReplyForm(request.POST, item=item) if is_reply else CommentForm(request.POST, item=item)

    if form.is_valid():
        if not Comment.check_rate_limits(request.user):
            form.add_error(None, f"Можно оставить не больше {settings.COMMENT_RATE_LIMIT} комментариев за сутки")
        else:
            comment = form.save(author=request.user, request=request, commit=False)
            comment.save()
            counters.comment_created(comment)
            notification.comment_created(comment)
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
        id=comment_id,
    )
    if comment.author_id != request.user.id:
        raise Http404()
    if not comment.is_editable():
        messages.error(
            request,
            f"Комментарий можно редактировать только первые {settings.COMMENT_EDIT_PERIOD.days} дней",
        )
        return redirect(f"{comment.item.get_absolute_url()}#comment-{comment.id}")

    is_reply = bool(comment.reply_to_id)
    form_class = ReplyForm if is_reply else CommentForm
    form = form_class(request.POST or None, item=comment.item, instance=comment)
    form.fields.pop("vibe", None)
    if is_reply:
        form.fields["text"].widget = deepcopy(CommentForm.base_fields["text"].widget)

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
        id=comment_id,
    )
    if comment.author_id != request.user.id:
        raise Http404()
    if not comment.is_deletable():
        messages.error(
            request,
            f"Комментарий можно удалить только первые {settings.COMMENT_DELETE_PERIOD.days} дней",
        )
        return redirect(f"{comment.item.get_absolute_url()}#comment-{comment.id}")

    comment.delete(by=request.user)
    counters.comment_deleted(comment)

    url = comment.item.get_absolute_url()
    if comment.reply_to_id:
        return redirect(f"{url}#comment-{comment.reply_to_id}")
    return redirect(f"{url}#comments")
