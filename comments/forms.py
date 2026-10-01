from django import forms

from comments.models import Comment
from common.request import parse_ip_address, parse_useragent


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("vibe", "text")
        widgets = {
            "vibe": forms.RadioSelect(),
            "text": forms.Textarea(attrs={
                "placeholder": "Расскажите, как всё прошло",
                "maxlength": 3000,
            }),
        }
        labels = {
            "vibe": "Как вам?",
            "text": "Комментарий",
        }
        error_messages = {
            "vibe": {"required": "Выберите, как вам", "invalid_choice": "Выберите, как вам"},
            "text": {
                "required": "Комментарий пустой",
                "max_length": "Слишком длинный комментарий (максимум 3000 символов)",
            },
        }

    def __init__(self, *args, item, **kwargs):
        self.item = item
        super().__init__(*args, **kwargs)
        self.fields["vibe"].required = True
        self.fields["vibe"].choices = Comment.VIBES  # ModelForm adds a blank option because the model field is nullable
        self.fields["text"].max_length = 3000

    def save(self, *, author, request, commit=True):
        comment = super().save(commit=False)
        comment.author = author
        comment.item = self.item
        comment.ipaddress = parse_ip_address(request)
        comment.useragent = parse_useragent(request)
        if commit:
            comment.save()
        return comment


class ReplyForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("text", "reply_to")
        widgets = {
            "text": forms.TextInput(attrs={
                "placeholder": "Ваш ответ",
                "maxlength": 3000,
            }),
            "reply_to": forms.HiddenInput(),
        }
        labels = {"text": "Ответ"}
        error_messages = {
            "text": {
                "required": "Комментарий пустой",
                "max_length": "Слишком длинный комментарий (максимум 3000 символов)",
            },
            "reply_to": {"required": "Нет комментария для ответа", "invalid_choice": "Нельзя ответить на этот комментарий"},
        }

    def __init__(self, *args, item, **kwargs):
        self.item = item
        super().__init__(*args, **kwargs)
        self.fields["text"].max_length = 3000
        self.fields["reply_to"].queryset = Comment.objects.filter(
            item=item,
            reply_to__isnull=True,
            deleted_at__isnull=True,
        )

    def save(self, *, author, request, commit=True):
        comment = super().save(commit=False)
        comment.author = author
        comment.item = self.item
        comment.vibe = None
        comment.ipaddress = parse_ip_address(request)
        comment.useragent = parse_useragent(request)
        if commit:
            comment.save()
        return comment
