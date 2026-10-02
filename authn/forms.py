from django import forms

from common.images import is_hosted_image
from users.models import User


class TelegramSignupForm(forms.Form):
    full_name = forms.CharField(
        label="Имя",
        max_length=128,
        strip=True,
        widget=forms.TextInput(),
        error_messages={"required": "Заполните поле", "max_length": "Слишком длинное значение"},
    )
    email = forms.EmailField(
        label="Почта",
        widget=forms.EmailInput(),
        error_messages={"required": "Заполните поле", "invalid": "Нужна настоящая почта"},
    )
    city = forms.CharField(
        label="Город",
        max_length=128,
        strip=True,
        widget=forms.TextInput(),
        error_messages={"required": "Заполните поле", "max_length": "Слишком длинное значение"},
    )
    country = forms.CharField(
        label="Страна",
        max_length=128,
        strip=True,
        widget=forms.TextInput(),
        error_messages={"required": "Заполните поле", "max_length": "Слишком длинное значение"},
    )
    avatar = forms.URLField(
        label="Аватар",
        required=False,
        assume_scheme="https",
    )
    contact = forms.CharField(
        label="Контакт",
        max_length=256,
        strip=True,
        widget=forms.TextInput(),
        error_messages={"required": "Заполните поле", "max_length": "Слишком длинное значение"},
    )

    def __init__(self, *args, telegram_data=None, **kwargs):
        data = telegram_data or {}
        username = data.get("username")
        name = " ".join(part for part in (data.get("first_name"), data.get("last_name")) if part).strip()
        kwargs.setdefault("initial", {
            "full_name": name[:128],
            "email": "",
            "city": "",
            "country": "",
            "contact": f"@{username}"[:256] if username else "",
        })
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Эта почта уже есть. Войдите через Клуб и привяжите бота там.")
        return email

    def clean_avatar(self):
        avatar = (self.cleaned_data.get("avatar") or "").strip()
        if avatar and not is_hosted_image(avatar):
            raise forms.ValidationError("Картинка должна быть загружена")
        return avatar
