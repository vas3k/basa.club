from django import forms

from comments.models import Comment


class CommentForm(forms.Form):
    text = forms.CharField(
        label="Комментарий",
        required=True,
        strip=True,
        widget=forms.Textarea(),
        error_messages={"required": "Комментарий пустой"},
    )
    reply_to = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput(),
    )

    def __init__(self, *args, item, **kwargs):
        self.item = item
        super().__init__(*args, **kwargs)

    def clean_reply_to(self):
        reply_id = self.cleaned_data.get("reply_to")
        if not reply_id:
            return None
        parent = Comment.objects.select_related("reply_to__reply_to").filter(
            pk=reply_id,
            item=self.item,
            deleted_at__isnull=True,
        ).first()
        if not parent:
            raise forms.ValidationError("Ответ должен быть к комментарию этого объявления")
        if parent.reply_to_id and parent.reply_to and parent.reply_to.reply_to_id:
            raise forms.ValidationError("3 уровня комментариев это максимум")
        return parent
