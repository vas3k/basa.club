from django import forms

from users.forms import WelcomeForm
from users.models import User


class TelegramSignupForm(WelcomeForm):
    bio = forms.CharField(
        label="Пара слов о себе",
        required=True,
        max_length=5000,
        strip=True,
        help_text="Расскажите о себе. Не менее 70 букв.",
        widget=forms.Textarea(attrs={"rows": 5}),
        error_messages={"required": "Расскажите о себе", "max_length": "Слишком длинное значение"},
    )
    email = forms.EmailField(
        max_length=User._meta.get_field("email").max_length,
        label="Почта",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
        error_messages={
            "required": "Укажите почту",
            "invalid": "Введите корректный адрес почты",
            "unique": "Эта почта уже есть. Войдите через Клуб и привяжите бота там.",
        },
    )

    class Meta:
        model = User
        fields = (*WelcomeForm.Meta.fields, "email")

    def __init__(self, *args, telegram_data=None, **kwargs):
        data = telegram_data or {}
        name = " ".join(part for part in (data.get("first_name"), data.get("last_name")) if part).strip()
        kwargs.setdefault("initial", {"full_name": name[:64]})
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.all_objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Эта почта уже есть. Войдите через Клуб и привяжите бота там.")
        return email
