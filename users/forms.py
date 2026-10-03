from django import forms

from common.images import is_hosted_image
from geo.models import GeoCity, GeoCountry
from users.models import User

EVERYWHERE = "everywhere"


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


class WelcomeForm(forms.ModelForm):
    full_name = forms.CharField(
        label="Имя",
        max_length=User._meta.get_field("full_name").max_length,
        strip=True,
        widget=forms.TextInput(),
        error_messages={"required": "Заполните поле", "max_length": "Слишком длинное значение"},
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
    contact = forms.CharField(
        label="Контакты",
        max_length=User._meta.get_field("contact").max_length,
        required=False,
        strip=True,
        widget=forms.TextInput(),
        error_messages={"max_length": "Слишком длинное значение"},
    )
    # Posted values are geo ids (or "everywhere"). save() stores the place names.
    country = forms.CharField(required=False, widget=forms.HiddenInput())
    city = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ("full_name", "avatar", "bio", "contact", "country", "city")

    def clean_avatar(self):
        avatar = (self.cleaned_data.get("avatar") or "").strip()
        if avatar and not is_hosted_image(avatar):
            raise forms.ValidationError("Картинка должна быть загружена")
        return avatar or None

    def clean(self):
        cleaned = super().clean()
        country_id = (cleaned.get("country") or "").strip()
        city_id = (cleaned.get("city") or "").strip()

        if not country_id:
            self.add_error("country", "Выберите страну или «Весь мир»")
            return cleaned

        if country_id == EVERYWHERE:
            cleaned["country_id"] = EVERYWHERE
            cleaned["city_id"] = EVERYWHERE
            cleaned["country"] = ""
            cleaned["city"] = ""
            return cleaned

        country = GeoCountry.objects.filter(pk=country_id).first()
        if not country:
            self.add_error("country", "Выберите страну из списка")
            return cleaned

        if not city_id or city_id == EVERYWHERE:
            cleaned["country_id"] = country.id
            cleaned["city_id"] = EVERYWHERE
            cleaned["country"] = country.name
            cleaned["city"] = ""
            return cleaned

        city = GeoCity.objects.filter(pk=city_id, country=country).first()
        if not city:
            self.add_error("city", "Выберите город из списка")
            return cleaned

        cleaned["country_id"] = country.id
        cleaned["city_id"] = city.id
        cleaned["country"] = country.name
        cleaned["city"] = city.name
        return cleaned
