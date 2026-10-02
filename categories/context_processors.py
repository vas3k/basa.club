from categories.counters import counts
from categories.models import Category


def categories(request):
    country_id = getattr(request, "country_id", None) or "everywhere"
    city_id = getattr(request, "city_id", None) or "everywhere"
    tree = list(Category.objects.filter(parent__isnull=True).prefetch_related("children"))
    for category in tree:
        counted = counts(category.id, country_id, city_id)
        category.items_count = counted.get(category.id, 0)
        for child in category.children.all():
            child.items_count = counted.get(child.id, 0)

    kwargs = request.resolver_match.kwargs if request.resolver_match else {}
    category_id = kwargs.get("category")
    subcategory_id = kwargs.get("subcategory")

    current_category = None
    current_subcategory = None
    for category in tree:
        if category.id == category_id:
            current_category = category
            for child in category.children.all():
                if child.id == subcategory_id:
                    current_subcategory = child
            break

    return {
        "categories": tree,
        "current_category": current_category,
        "current_subcategory": current_subcategory,
    }
