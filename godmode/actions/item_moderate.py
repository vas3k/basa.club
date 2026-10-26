from django import forms
from django.conf import settings
from django.db import transaction
from django.shortcuts import render

from counters import counters
from items.models import Item
from notifications import notification
from search import search


class ItemModerateForm(forms.Form):
    reason = forms.ChoiceField(
        label="Причина",
        choices=[(reason["title"], reason["title"]) for reason in settings.ITEM_MODERATION_REASONS],
        widget=forms.RadioSelect,
        error_messages={"required": "Выберите причину"},
    )

    def clean_reason(self):
        reason = (self.cleaned_data.get("reason") or "").strip()
        known = {row["title"] for row in settings.ITEM_MODERATION_REASONS}
        if reason not in known:
            raise forms.ValidationError("Выберите причину")
        return reason


def get_moderate_action(request, obj: Item, **context):
    return render(request, "godmode/actions/item_moderate.html", {
        **context,
        "form": ItemModerateForm(),
        "reasons": settings.ITEM_MODERATION_REASONS,
    })


def post_moderate_action(request, obj: Item, **context):
    form = ItemModerateForm(request.POST)
    if not form.is_valid():
        return render(request, "godmode/actions/item_moderate.html", {
            **context,
            "form": form,
            "reasons": settings.ITEM_MODERATION_REASONS,
        })

    selected = next(
        reason for reason in settings.ITEM_MODERATION_REASONS
        if reason["title"] == form.cleaned_data["reason"]
    )
    was_listed = obj.is_listed
    obj.visibility = Item.VISIBILITY_DRAFT
    obj.moderator_comment = f"{selected['title']} {selected['description']}"
    obj.save(update_fields=["visibility", "moderator_comment"])
    search.update_item_index(obj)
    if was_listed:
        counters.item_hidden(obj)

    transaction.on_commit(lambda: notification.item_moderated(obj, reason=selected["title"]))

    return render(request, "godmode/message.html", {
        **context,
        "title": "Пост скрыт",
        "message": f"«{obj.title}» ушёл в черновики: {selected['title']}",
    })
