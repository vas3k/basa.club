import calendar
import json
from datetime import timedelta

from django import forms
from django.utils import formats, timezone

from categories.models import Category
from common.contacts import CONTACT_TYPES
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
        max_length=100,
        widget=forms.HiddenInput(),
        error_messages={"max_length": "Слишком длинное значение"},
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
            ("", "➕"),
            *Item.PREFIXES,
        ),
        widget=forms.Select(attrs={"aria-label": "Префикс"}),
    )
    title = forms.CharField(
        label="Заголовок",
        max_length=Item._meta.get_field("title").max_length,
        strip=True,
        widget=forms.TextInput(attrs={"placeholder": "Заголовок, краткое описание", "minlength": 8}),
        error_messages={
            "required": "Нужен заголовок",
            "min_length": "Слишком короткий заголовок",
            "max_length": "Слишком длинный заголовок",
        },
    )
    description = forms.CharField(
        label="Описание",
        required=False,
        max_length=5000,
        strip=True,
        widget=forms.Textarea(),
        error_messages={"max_length": "Слишком длинное описание"},
    )
    location = forms.CharField(
        label="Место",
        required=False,
        strip=True,
        max_length=512,
        widget=forms.TextInput(attrs={"placeholder": "Адрес или ссылка на карту", "minlength": 5}),
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
        max_length=128,
        widget=forms.TextInput(attrs={
            "placeholder": "Например, SUMMER",
            "autocomplete": "off",
            "spellcheck": "false",
            "minlength": 3,
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

    QUERY_FIELDS = (
        "country", "city", "category", "subcategory",
        "prefix", "title", "description", "location", "contacts", "promo_code",
    )

    @classmethod
    def initial_from_query(cls, params, initial):
        result = dict(initial)
        if "country" in params:
            result["country"] = (params.get("country") or "").strip() or "everywhere"
            if "city" not in params:
                result["city"] = None
        if "city" in params:
            city = (params.get("city") or "").strip()
            result["city"] = None if city in {"", "everywhere"} else city
        for name in ("category", "subcategory", "title", "description", "location", "promo_code"):
            if name in params:
                result[name] = params.get(name) or ""
        if "prefix" in params:
            prefix = (params.get("prefix") or "").strip()
            result["prefix"] = prefix if prefix in dict(Item.PREFIXES) else ""
        if "contacts" in params:
            raw = params.get("contacts") or ""
            try:
                parsed = json.loads(raw) if raw else []
            except (TypeError, ValueError):
                parsed = None
            if isinstance(parsed, list):
                result["contacts"] = parsed
        return result

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
        country = GeoCountry.objects.filter(id=raw).first()
        if not country:
            raise forms.ValidationError("Нет такой страны")
        return country

    def clean_prefix(self):
        return self.cleaned_data.get("prefix") or None

    def clean_title(self):
        title = self.cleaned_data["title"]
        if len(title) < 8:
            raise forms.ValidationError(self.fields["title"].error_messages["min_length"], code="min_length")
        return title

    def clean_location(self):
        location = self.cleaned_data["location"]
        if location and len(location) < 5:
            raise forms.ValidationError(self.fields["location"].error_messages["min_length"], code="min_length")
        return location

    def clean_promo_code(self):
        promo_code = self.cleaned_data["promo_code"]
        if promo_code and len(promo_code) < 3:
            raise forms.ValidationError(self.fields["promo_code"].error_messages["min_length"], code="min_length")
        return promo_code

    def clean_contacts(self):
        raw = self.cleaned_data.get("contacts") or []
        if not isinstance(raw, list):
            raise forms.ValidationError("Неверный список контактов")
        if len(raw) > 15:
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
            if len(text) > 256 or len(comment) > 256:
                raise forms.ValidationError("Контакт длиннее 256 символов")
            if len(contact_type) > 32:
                raise forms.ValidationError("Неверный контакт")
            if contact_type not in CONTACT_TYPES:
                contact_type = "custom"
            cleaned.append({"type": contact_type, "text": text, "comment": comment})
        return cleaned

    def clean_images(self):
        raw = self.cleaned_data.get("images") or []
        if not isinstance(raw, list):
            raise forms.ValidationError("Неверный список картинок")
        if len(raw) > 15:
            raise forms.ValidationError("Слишком много картинок")

        cleaned = []
        for row in raw:
            if not isinstance(row, dict):
                raise forms.ValidationError("Неверная картинка")
            url = row.get("image")
            if not isinstance(url, str):
                raise forms.ValidationError("Неверная картинка")
            url = url.strip()
            if not url:
                continue
            if len(url) > 2048:
                raise forms.ValidationError("Слишком длинная ссылка на картинку")
            cleaned.append({"image": url})
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

    def save(self, commit=True):
        item = super().save(commit=False)

        choice = self.cleaned_data.get("expires_in") or "never"
        now = timezone.now()
        if choice == "day":
            item.expires_at = now + timedelta(days=1)
        elif choice == "week":
            item.expires_at = now + timedelta(days=7)
        elif choice in {"month", "quarter", "year"}:
            months = {"month": 1, "quarter": 3, "year": 12}[choice]
            month_index = now.month - 1 + months
            year = now.year + month_index // 12
            month = month_index % 12 + 1
            day = min(now.day, calendar.monthrange(year, month)[1])
            item.expires_at = now.replace(year=year, month=month, day=day)
        elif choice != "keep":
            item.expires_at = None

        if commit:
            item.save()
        return item
