from django import forms

from geo.models import GeoCity, GeoCountry
from users.models import User

EVERYWHERE = "everywhere"


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
    # The picker submits geo IDs, but the profile stores country and city names.
    country = forms.CharField(required=False, widget=forms.HiddenInput())
    city = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ("full_name", "avatar", "bio", "country", "city")

    def clean_avatar(self):
        avatar = (self.cleaned_data.get("avatar") or "").strip()
        return avatar or None

    def clean_country(self):
        country_id = self.cleaned_data["country"].strip()
        if not country_id:
            raise forms.ValidationError("Выберите страну или «Весь мир»")
        if country_id == EVERYWHERE:
            self.cleaned_data["country_id"] = EVERYWHERE
            return ""

        country = GeoCountry.objects.filter(pk=country_id).first()
        if not country:
            raise forms.ValidationError("Выберите страну из списка")

        self.cleaned_data["country_id"] = country.id
        return country.name

    def clean_city(self):
        country_id = self.cleaned_data.get("country_id")
        city_id = self.cleaned_data["city"].strip()
        if not country_id or country_id == EVERYWHERE or not city_id or city_id == EVERYWHERE:
            self.cleaned_data["city_id"] = EVERYWHERE
            return ""

        city = GeoCity.objects.filter(pk=city_id, country_id=country_id).first()
        if not city:
            raise forms.ValidationError("Выберите город из списка")

        self.cleaned_data["city_id"] = city.id
        return city.name


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
