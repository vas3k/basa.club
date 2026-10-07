from notifications.subscriptions import is_subscribed, listing_target

LISTING_VIEWS = {"index", "country_index", "listing", "listing_category", "listing_subcategory"}


def listing_subscription(request):
    match = getattr(request, "resolver_match", None)
    if not match or match.url_name not in LISTING_VIEWS:
        return {"show_listing_subscribe": False, "listing_subscribed": False}

    country_id, city_id, category_id, query = listing_target(request)
    return {
        "show_listing_subscribe": True,
        "listing_subscribed": is_subscribed(request.user, country_id, city_id, category_id, query),
    }
