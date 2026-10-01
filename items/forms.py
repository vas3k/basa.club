from django import forms
from django.utils import timezone

from categories.models import Category
from geo.models import GeoCity, GeoCountry
from items.models import Item


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

    class Meta:
        model = Item
        fields = ("country", "city", "category", "subcategory", "title", "description")

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

    def save(self, *, author=None, is_draft=False, commit=True):
        item = super().save(commit=False)
        if author is not None:
            item.author = author

        item.visibility = Item.VISIBILITY_DRAFT if is_draft else Item.VISIBILITY_VISIBLE
        if is_draft:
            item.published_at = None
        elif not item.published_at:
            item.published_at = timezone.now()

        if commit:
            item.save()
        return item
