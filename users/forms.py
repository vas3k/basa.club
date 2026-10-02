from django import forms

from common.images import is_hosted_image
from geo.models import GeoCountry


class ProfileForm(forms.Form):
    full_name = forms.CharField(
        label="Имя",
        max_length=128,
        required=False,
        strip=True,
        widget=forms.TextInput(),
        error_messages={"max_length": "Слишком длинное значение"},
    )
    city = forms.CharField(
        label="Город",
        max_length=128,
        required=False,
        strip=True,
        widget=forms.TextInput(),
        error_messages={"max_length": "Слишком длинное значение"},
    )
    country = forms.ChoiceField(
        label="Страна",
        required=False,
        choices=[],
        widget=forms.Select(),
    )
    avatar = forms.URLField(
        label="Аватар",
        required=False,
        assume_scheme="https",
    )
    bio = forms.CharField(
        label="О себе",
        required=False,
        strip=True,
        widget=forms.Textarea(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [("", "—")]
        for country in GeoCountry.objects.all():
            label = f"{country.icon} {country.name}".strip() if country.icon else country.name
            choices.append((country.name, label))
        current = (self.initial.get("country") or "").strip()
        if current and current not in {value for value, _label in choices}:
            choices.append((current, current))
        self.fields["country"].choices = choices

    def clean_avatar(self):
        avatar = (self.cleaned_data.get("avatar") or "").strip()
        if avatar and not is_hosted_image(avatar):
            raise forms.ValidationError("Картинка должна быть загружена")
        return avatar
