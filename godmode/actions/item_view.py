from django.shortcuts import redirect

from items.models import Item


def view_item_action(request, item: Item, **context):
    return redirect(item.get_absolute_url())
