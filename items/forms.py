import calendar
from datetime import timedelta

from django import forms
from django.utils import formats, timezone

from categories.models import Category
from common.contacts import CONTACT_MAX_COUNT, CONTACT_MAX_LENGTH, CONTACT_TYPES
from geo.models import GeoCity, GeoCountry
from items.models import Item

EXPIRES_CHOICES = (
    ("never", "Никогда"),
    ("day", "1 день"),
    ("week", "1 неделю"),
    ("month", "1 месяц"),
    ("quarter", "3 месяца"),
    ("year", "1 год"),
)


class ItemForm(forms.ModelForm):
    country = forms.CharField(
        label="Страна",
        required=False,
        widget=forms.HiddenInput(),
    )
    city = forms.ModelChoiceField(
        label="Город",
        queryset=GeoCity.objects.all(),
        required=False,
        error_messages={"invalid_choice": "Нет такого города"},
    )
    category = forms.ModelChoiceField(
        label="Категория",
        queryset=Category.objects.filter(parent__isnull=True),
        error_messages={"required": "Выберите категорию", "invalid_choice": "Нет такой категории"},
    )
    subcategory = forms.ModelChoiceField(
        label="Подкатегория",
        queryset=Category.objects.filter(parent__isnull=False),
        error_messages={"required": "Выберите подкатегорию", "invalid_choice": "Нет такой подкатегории"},
    )
    prefix = forms.ChoiceField(
        required=False,
        choices=(
            ("", ""),
            *Item.PREFIXES,
        ),
        widget=forms.Select(attrs={"aria-label": "Префикс"}),
    )
    title = forms.CharField(
        label="Заголовок",
        min_length=8,
        max_length=Item._meta.get_field("title").max_length,
        strip=True,
        widget=forms.TextInput(attrs={"placeholder": "Заголовок, краткое описание"}),
        error_messages={
            "required": "Нужен заголовок",
            "min_length": "Слишком короткий заголовок",
            "max_length": "Слишком длинный заголовок",
        },
    )
    description = forms.CharField(
        label="Описание",
        required=False,
        strip=True,
        widget=forms.Textarea(),
    )
    location = forms.CharField(
        label="Место",
        required=False,
        strip=True,
        min_length=5,
        max_length=Item._meta.get_field("location").max_length,
        widget=forms.TextInput(attrs={"placeholder": "Адрес или ссылка на карту"}),
        error_messages={
            "min_length": "Слишком короткое место",
            "max_length": "Слишком длинное место",
        },
    )
    contacts = forms.JSONField(
        required=False,
        error_messages={"invalid": "Неверный список контактов"},
    )
    images = forms.JSONField(
        required=False,
        error_messages={"invalid": "Неверный список картинок"},
    )
    promo_code = forms.CharField(
        label="Промокод",
        required=False,
        strip=True,
        min_length=3,
        max_length=Item._meta.get_field("promo_code").max_length,
        widget=forms.TextInput(attrs={
            "placeholder": "Например, SUMMER",
            "autocomplete": "off",
            "spellcheck": "false",
        }),
        error_messages={
            "min_length": "Слишком короткий промокод",
            "max_length": "Слишком длинный промокод",
        },
    )
    expires_in = forms.ChoiceField(
        label="Истекает через:",
        choices=EXPIRES_CHOICES,
        initial="never",
        required=False,
    )

    class Meta:
        model = Item
        fields = (
            "country", "city", "category", "subcategory",
            "prefix", "title", "description", "images", "location", "contacts", "promo_code",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.initial.get("country") and not self.instance.country_id:
            self.initial["country"] = "everywhere"
        if not self.instance.expires_at:
            return
        shown = formats.date_format(self.instance.expires_at, "j E Y")
        self.fields["expires_in"].choices = (
            ("keep", shown),
            *EXPIRES_CHOICES,
        )
        if not self.is_bound:
            self.initial["expires_in"] = "keep"

    def clean_country(self):
        raw = (self.cleaned_data.get("country") or "").strip()
        if not raw:
            raise forms.ValidationError("Выберите страну или «Весь мир»")
        if raw == "everywhere":
            return None
        country = GeoCountry.objects.filter(pk=raw).first()
        if not country:
            raise forms.ValidationError("Нет такой страны")
        return country

    def clean_prefix(self):
        return self.cleaned_data.get("prefix") or None

    def clean_contacts(self):
        raw = self.cleaned_data.get("contacts") or []
        if not isinstance(raw, list):
            raise forms.ValidationError("Неверный список контактов")
        if len(raw) > CONTACT_MAX_COUNT:
            raise forms.ValidationError("Слишком много контактов")

        cleaned = []
        for row in raw:
            if not isinstance(row, dict):
                raise forms.ValidationError("Неверный контакт")
            contact_type = row.get("type")
            text = row.get("text")
            comment = row.get("comment") or ""
            if not isinstance(contact_type, str) or not isinstance(text, str) or not isinstance(comment, str):
                raise forms.ValidationError("Неверный контакт")
            contact_type = contact_type.strip()
            text = text.strip()
            comment = comment.strip()
            if not text and not comment:
                continue
            if not text:
                raise forms.ValidationError("У контакта нет значения")
            if len(text) < 3:
                raise forms.ValidationError("Слишком короткий контакт")
            if len(contact_type) > CONTACT_MAX_LENGTH or len(text) > CONTACT_MAX_LENGTH or len(comment) > CONTACT_MAX_LENGTH:
                raise forms.ValidationError("Контакт длиннее 128 символов")
            if contact_type not in CONTACT_TYPES:
                contact_type = "custom"
            cleaned.append({"type": contact_type, "text": text, "comment": comment})
        return cleaned

    def clean_images(self):
        raw = self.cleaned_data.get("images") or []
        if not isinstance(raw, list):
            raise forms.ValidationError("Неверный список картинок")

        cleaned = []
        for row in raw:
            if not isinstance(row, dict):
                raise forms.ValidationError("Неверная картинка")
            url = row.get("image")
            if not isinstance(url, str):
                raise forms.ValidationError("Неверная картинка")
            cleaned.append({"image": url.strip()})
        return cleaned

    def clean(self):
        cleaned_data = super().clean()

        country = cleaned_data.get("country")
        city = cleaned_data.get("city")
        if not country:
            cleaned_data["city"] = None
        elif city and city.country_id != country.id:
            self.add_error("city", "Этот город не из выбранной страны")

        category = cleaned_data.get("category")
        subcategory = cleaned_data.get("subcategory")
        if category and subcategory and subcategory.root_id != category.id:
            self.add_error("subcategory", "Эта подкатегория не из выбранной категории")

        return cleaned_data

    def save(self, *, author=None, is_draft=False, keep_visibility=False, commit=True):
        item = super().save(commit=False)
        if author is not None:
            item.author = author

        if not keep_visibility:
            item.visibility = Item.VISIBILITY_DRAFT if is_draft else Item.VISIBILITY_VISIBLE
            if is_draft:
                item.published_at = None
            elif not item.published_at:
                item.published_at = timezone.now()

        self._apply_expiry(item)

        if commit:
            item.save()
        return item

    def _apply_expiry(self, item):
        choice = self.cleaned_data.get("expires_in") or "never"
        if choice == "keep":
            return
        item.expires_at = expires_at_for(choice)


def expires_at_for(choice):
    now = timezone.now()
    if choice == "day":
        return now + timedelta(days=1)
    if choice == "week":
        return now + timedelta(days=7)
    if choice == "month":
        return add_months(now, 1)
    if choice == "quarter":
        return add_months(now, 3)
    if choice == "year":
        return add_months(now, 12)
    return None


def add_months(moment, months):
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)
