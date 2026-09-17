from categories.models import Category


def categories(request):
    tree = list(Category.objects.filter(parent__isnull=True).prefetch_related("children"))

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
