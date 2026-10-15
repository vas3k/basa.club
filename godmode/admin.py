from dataclasses import dataclass, field
from typing import Callable, Optional

from django import forms
from django.contrib.postgres.fields import ArrayField as PostgresArrayField
from django.contrib.postgres.forms import SimpleArrayField
from django.db import models
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.safestring import mark_safe

from users.models import User


@dataclass
class ClubAdminField:
    name: str
    display_name: str
    model_field: Optional[models.Field] = None
    list_template: Optional[str] = None

    @classmethod
    def from_model_field(cls, model_field: models.Field):
        return cls(
            name=model_field.name or "Unknown",
            display_name=model_field.verbose_name or model_field.name.replace("_", " ").title(),
            model_field=model_field,
        )

    def render_list(self, value):
        if self.list_template:
            return mark_safe(render_to_string(self.list_template, {
                "value": value,
            }))

        try:
            if value is None:
                rendered = ""
            elif hasattr(value, "strftime"):
                rendered = value.strftime("%Y-%m-%d %H:%M")
            elif isinstance(value, bool):
                rendered = "✅" if value else "❌"
            else:
                rendered = str(value)
                if self.model_field is not None and self.model_field.choices:
                    rendered = str(dict(self.model_field.flatchoices).get(value, rendered))
                if len(rendered) > 150:
                    rendered = rendered[:150] + "..."
        except Exception:
            rendered = "???"
        return escape(rendered)


def is_admin(user: User) -> bool:
    return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))


@dataclass
class ClubAdminAction:
    title: str = None
    get: Callable = None
    post: Callable = None

    def has_access(self, user: User) -> bool:
        return is_admin(user)


@dataclass
class ClubAdminModel:
    model: type[models.Model] = None
    title: str = None
    icon: str = None
    name: str = None
    title_field: str = None

    list_fields: list | ClubAdminField = field(default_factory=list)
    edit_fields: list = field(default_factory=list)
    hide_fields: list = field(default_factory=list)
    allow_delete: bool = True

    actions: dict[str, ClubAdminAction] = field(default_factory=dict)

    def get_absolute_url(self):
        return f"/godmode/{self.name}/" if self.name else None

    def has_list_access(self, user: User) -> bool:
        return is_admin(user)

    def has_edit_access(self, user: User) -> bool:
        if self.model is User:
            return bool(user.is_superuser)
        return is_admin(user)

    def has_create_access(self, user: User) -> bool:
        if self.model is User:
            return bool(user.is_superuser)
        return is_admin(user)

    def has_delete_access(self, user: User) -> bool:
        return self.allow_delete and is_admin(user)

    def actions_for(self, user: User) -> dict[str, ClubAdminAction]:
        return {
            code: action
            for code, action in self.actions.items()
            if action.has_access(user)
        }

    def get_list_fields(self):
        fields = []
        if self.list_fields:
            for list_field in self.list_fields:
                if isinstance(list_field, ClubAdminField):
                    list_field.model_field = self.model._meta.get_field(list_field.name)
                    fields.append(list_field)
                else:
                    fields.append(ClubAdminField.from_model_field(self.model._meta.get_field(list_field)))
        else:
            fields = [
                ClubAdminField.from_model_field(model_field)
                for model_field in self.model._meta.fields
                if model_field.name not in self.hide_fields
            ]
        return fields

    def get_form_class(self):
        admin_model = self

        class DynamicModelForm(forms.ModelForm):
            class Meta:
                model = admin_model.model
                fields = admin_model.edit_fields if admin_model.edit_fields else [
                    model_field.name for model_field in admin_model.model._meta.fields
                    if model_field.editable and model_field.name not in admin_model.hide_fields
                ]

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                for field_name, form_field in list(self.fields.items()):
                    model_field = admin_model.model._meta.get_field(field_name)

                    if isinstance(model_field, models.ForeignKey):
                        form_field.widget = forms.TextInput()
                        if self.instance and self.instance.id:
                            related_obj = getattr(self.instance, field_name, None)
                            if related_obj:
                                form_field.initial = related_obj.id

                    if isinstance(model_field, PostgresArrayField):
                        form_field = self.fields[field_name] = SimpleArrayField(
                            forms.CharField(max_length=model_field.base_field.max_length),
                            label=form_field.label,
                            initial=form_field.initial,
                        )

                    if not model_field.null and not model_field.blank and not model_field.has_default():
                        form_field.required = True
                    else:
                        form_field.required = False

        return DynamicModelForm


@dataclass
class ClubAdminPage:
    title: str = None
    icon: str = None
    name: str = None

    view: Callable = None

    def get_absolute_url(self):
        return f"/godmode/page/{self.name}/" if self.name else None

    def has_access(self, user: User) -> bool:
        return is_admin(user)


@dataclass
class ClubAdminGroup:
    title: str = "Default Group"
    icon: str = ""
    models: list[ClubAdminModel | ClubAdminPage] = field(default_factory=list)


@dataclass
class ClubAdmin:
    title: str = "Admin"
    groups: list[ClubAdminGroup] = field(default_factory=list)
    foreign_key_templates: dict = field(default_factory=dict)

    def get_model(self, model_name: str) -> ClubAdminModel | None:
        for group in self.groups:
            for model in group.models:
                if isinstance(model, ClubAdminModel) and model.name == model_name:
                    return model
        return None

    def get_page(self, page_name: str) -> ClubAdminPage | None:
        for group in self.groups:
            for model in group.models:
                if isinstance(model, ClubAdminPage) and model.name == page_name:
                    return model
        return None

    def has_access(self, user: User) -> bool:
        return is_admin(user)
