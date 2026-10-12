from django import forms

from geo.models import GeoCity, GeoCountry
from users.models import User

EVERYWHERE = "everywhere"


def apply_place(form):
    cleaned = form.cleaned_data
    country_id = (cleaned.get("country") or "").strip()
    city_id = (cleaned.get("city") or "").strip()

    if not country_id:
        form.add_error("country", "Выберите страну или «Весь мир»")
        return cleaned

    if country_id == EVERYWHERE:
        cleaned["country_id"] = EVERYWHERE
        cleaned["city_id"] = EVERYWHERE
        cleaned["country"] = ""
        cleaned["city"] = ""
        return cleaned

    country = GeoCountry.objects.filter(pk=country_id).first()
    if not country:
        form.add_error("country", "Выберите страну из списка")
        return cleaned

    if not city_id or city_id == EVERYWHERE:
        cleaned["country_id"] = country.id
        cleaned["city_id"] = EVERYWHERE
        cleaned["country"] = country.name
        cleaned["city"] = ""
        return cleaned

    city = GeoCity.objects.filter(pk=city_id, country=country).first()
    if not city:
        form.add_error("city", "Выберите город из списка")
        return cleaned

    cleaned["country_id"] = country.id
    cleaned["city_id"] = city.id
    cleaned["country"] = country.name
    cleaned["city"] = city.name
    return cleaned


class ProfileForm(forms.ModelForm):
    full_name = forms.CharField(
        label="Ваше имя",
        min_length=5,
        max_length=64,
        required=False,
        strip=True,
        widget=forms.TextInput(),
        error_messages={
            "min_length": "Слишком короткое имя",
            "max_length": "Слишком длинное значение",
        },
    )
    avatar = forms.URLField(
        label="Аватар",
        required=False,
        assume_scheme="https",
    )
    bio = forms.CharField(
        label="Расскажите о себе",
        required=False,
        min_length=10,
        strip=True,
        widget=forms.Textarea(attrs={"rows": 3}),
        error_messages={"min_length": "Слишком короткий текст"},
    )
    country = forms.CharField(required=False, widget=forms.HiddenInput())
    city = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ("full_name", "avatar", "bio", "country", "city")

    def clean_avatar(self):
        avatar = (self.cleaned_data.get("avatar") or "").strip()
        return avatar or None

    def clean(self):
        super().clean()
        return apply_place(self)


class WelcomeForm(ProfileForm):
    full_name = forms.CharField(
        label="Ваше имя",
        min_length=5,
        max_length=64,
        required=True,
        strip=True,
        widget=forms.TextInput(),
        error_messages={
            "required": "Заполните поле",
            "min_length": "Слишком короткое имя",
            "max_length": "Слишком длинное значение",
        },
    )
    bio = forms.CharField(
        label="Расскажите о себе",
        required=False,
        min_length=10,
        strip=True,
        widget=forms.Textarea(attrs={"rows": 5}),
        error_messages={"min_length": "Слишком короткий текст"},
    )
    agree_data = forms.BooleanField(
        required=True,
        error_messages={"required": "Нужно согласие"},
    )
    agree_rules = forms.BooleanField(
        required=True,
        error_messages={"required": "Нужно согласие"},
    )
    agree_conduct = forms.BooleanField(
        required=True,
        error_messages={"required": "Нужно согласие"},
    )
