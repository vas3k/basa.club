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
    country = forms.ModelChoiceField(
        label="Страна",
        queryset=GeoCountry.objects.all(),
        error_messages={"required": "Выберите страну", "invalid_choice": "Нет такой страны"},
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
    title = forms.CharField(
        label="Заголовок",
        max_length=Item._meta.get_field("title").max_length,
        strip=True,
        widget=forms.TextInput(attrs={"placeholder": "Что предлагаете?"}),
        error_messages={"required": "Нужен заголовок", "max_length": "Слишком длинный заголовок"},
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
        max_length=Item._meta.get_field("location").max_length,
        widget=forms.TextInput(attrs={"placeholder": "Адрес или ссылка на карту"}),
        error_messages={"max_length": "Слишком длинное место"},
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
        max_length=Item._meta.get_field("promo_code").max_length,
        widget=forms.TextInput(attrs={
            "placeholder": "Например, SUMMER",
            "autocomplete": "off",
            "spellcheck": "false",
        }),
        error_messages={"max_length": "Слишком длинный промокод"},
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
            "title", "description", "images", "location", "contacts", "promo_code",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.expires_at:
            return
        shown = formats.date_format(self.instance.expires_at, "j E Y")
        self.fields["expires_in"].choices = (
            ("keep", shown),
            *EXPIRES_CHOICES,
        )
        if not self.is_bound:
            self.initial["expires_in"] = "keep"

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
        if country and city and city.country_id != country.id:
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
