from django import forms

from comments.models import Comment
from common.request import parse_ip_address, parse_useragent


class CommentForm(forms.ModelForm):
    vibe = forms.ChoiceField(
        label="Как вам?",
        choices=Comment.VIBES,
        widget=forms.RadioSelect(),
        error_messages={"required": "Выберите, как вам", "invalid_choice": "Выберите, как вам"},
    )
    text = forms.CharField(
        label="Комментарий",
        max_length=5000,
        widget=forms.Textarea(attrs={
            "placeholder": "Расскажите, как всё прошло",
        }),
        error_messages={
            "required": "Комментарий пустой",
            "max_length": "Слишком длинный комментарий (максимум 5000 символов)",
        },
    )

    class Meta:
        model = Comment
        fields = ("vibe", "text")

    def __init__(self, *args, item, **kwargs):
        self.item = item
        super().__init__(*args, **kwargs)

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
    text = forms.CharField(
        label="Ответ",
        max_length=5000,
        widget=forms.TextInput(attrs={
            "placeholder": "Ваш ответ",
        }),
        error_messages={
            "required": "Комментарий пустой",
            "max_length": "Слишком длинный комментарий (максимум 5000 символов)",
        },
    )
    reply_to = forms.ModelChoiceField(
        queryset=Comment.objects.none(),
        required=False,
        widget=forms.HiddenInput(),
        error_messages={
            "required": "Нет комментария для ответа",
            "invalid_choice": "Нельзя ответить на этот комментарий",
        },
    )

    class Meta:
        model = Comment
        fields = ("text", "reply_to")

    def __init__(self, *args, item, **kwargs):
        self.item = item
        super().__init__(*args, **kwargs)
        self.fields["reply_to"].queryset = Comment.objects.filter(
            item=item,
            reply_to__isnull=True,
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
