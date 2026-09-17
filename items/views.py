from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from categories.models import Category
from items.models import Item


def index_page(request):
    items = Item.objects.select_related("category", "subcategory", "country", "city", "author")
    if request.city_id != "everywhere":
        items = items.filter(city_id=request.city_id)
    elif request.country_id != "everywhere":
        items = items.filter(country_id=request.country_id)

    query = (request.GET.get("query") or "").strip()
    if query:
        items = items.filter(Q(title__icontains=query) | Q(description__icontains=query))

    return render(request, "index.html", {"items": items})


def listing_page(request, country, city, category=None, subcategory=None):
    if "country" not in request.COOKIES:
        request.country_id = country
        request.city_id = city

    if subcategory:
        get_object_or_404(Category, pk=subcategory, root_id=category)
    elif category:
        get_object_or_404(Category, pk=category, parent__isnull=True)

    items = Item.objects.select_related("category", "subcategory", "country", "city", "author")
    if subcategory:
        items = items.filter(subcategory_id=subcategory)
    elif category:
        items = items.filter(category_id=category)

    if request.city_id != "everywhere":
        items = items.filter(city_id=request.city_id)
    elif request.country_id != "everywhere":
        items = items.filter(country_id=request.country_id)

    query = (request.GET.get("query") or "").strip()
    if query:
        items = items.filter(Q(title__icontains=query) | Q(description__icontains=query))

    return render(request, "index.html", {"items": items})


def item_page(request, country, city, category, subcategory, item_id):
    item = get_object_or_404(
        Item.objects.select_related("category", "subcategory", "country", "city", "author"),
        pk=item_id,
        category_id=category,
        subcategory_id=subcategory,
    )
    return render(request, "items/item.html", {"item": item})
