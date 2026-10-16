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
        max_length=200,
        assume_scheme="https",
        error_messages={"max_length": "Слишком длинное значение"},
    )
    bio = forms.CharField(
        label="Пара слов о себе",
        required=False,
        max_length=5000,
        strip=True,
        widget=forms.Textarea(attrs={"rows": 3}),
        error_messages={"max_length": "Слишком длинное значение"},
    )
    country = forms.CharField(
        required=True,
        max_length=64,
        widget=forms.HiddenInput(),
        error_messages={"max_length": "Слишком длинное значение"},
    )
    city = forms.CharField(
        required=False,
        max_length=64,
        widget=forms.HiddenInput(),
        error_messages={"max_length": "Слишком длинное значение"},
    )

    class Meta:
        model = User
        fields = ("full_name", "avatar", "bio", "country", "city")

    def clean_avatar(self):
        avatar = (self.cleaned_data.get("avatar") or "").strip()
        return avatar or None

    def clean_country(self):
        country_id = self.cleaned_data["country"].strip()
        if not country_id:
            raise forms.ValidationError("Выберите страну")
        country = GeoCountry.objects.filter(id=country_id).first()
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

        city = GeoCity.objects.filter(id=city_id, country_id=country_id).first()
        if not city:
            raise forms.ValidationError("Выберите город из списка")

        self.cleaned_data["city_id"] = city.id
        return city.name


class WelcomeForm(ProfileForm):
    full_name = forms.CharField(
        label="Как вас зовут?",
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
        label="Пара слов о себе",
        required=False,
        max_length=5000,
        strip=True,
        widget=forms.Textarea(attrs={"rows": 5}),
        error_messages={"max_length": "Слишком длинное значение"},
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
