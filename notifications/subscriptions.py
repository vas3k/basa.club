import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone

from categories.models import Category
from geo.models import GeoCity, GeoCountry
from notifications.models import Subscription
from search import search

log = logging.getLogger(__name__)

EVERYWHERE = "everywhere"


class InvalidSubscription(LookupError):
    pass


def subscribe_to_geo(user, country_id, city_id):
    """Subscribe a user to new items in one country and city.

    country_id and city_id are geo primary keys, or "everywhere".
    """
    country_id, city_id = normalize_geo_ids(country_id, city_id)
    try:
        subscription, _created = Subscription.objects.get_or_create(
            user=user,
            country_id=country_id,
            city_id=city_id,
            category=None,
            query="",
        )
    except IntegrityError:
        subscription = Subscription.objects.get(
            user=user,
            country_id=country_id,
            city_id=city_id,
            category=None,
            query="",
        )
    log.info(
        "geo subscription user=%s country=%s city=%s",
        user.id,
        country_id,
        city_id,
    )
    return subscription


def toggle_subscription(user, country_id, city_id, category_id, query, include_online=False):
    """Create the listing subscription, or delete it if it already exists."""
    country = None
    city = None
    category = None
    country_id, city_id = normalize_geo_ids(country_id, city_id)
    query = (query or "").strip()[:Subscription.QUERY_MAX_LENGTH]

    if country_id:
        country = GeoCountry.objects.filter(id=country_id).first()
        if not country:
            raise InvalidSubscription(country_id)
    if city_id:
        city = GeoCity.objects.filter(id=city_id, country=country).first() if country else None
        if not city:
            raise InvalidSubscription(city_id)
    category_id = (category_id or "").strip()
    if category_id:
        category = Category.objects.filter(id=category_id).first()
        if not category:
            raise InvalidSubscription(category_id)

    existing = Subscription.objects.filter(
        user=user,
        country=country,
        city=city,
        category=category,
        query=query,
    ).first()
    if existing:
        existing.delete()
        return False

    try:
        Subscription.objects.create(
            user=user,
            country=country,
            city=city,
            category=category,
            query=query,
            include_online=bool(include_online),
        )
    except IntegrityError:
        return True
    return True


def unsubscribe(subscription_id, telegram_id):
    """Remove one subscription owned by this Telegram account.

    Returns "removed", "missing", or "forbidden". Other subscriptions stay.
    """
    try:
        subscription = Subscription.objects.select_related("user").get(id=subscription_id)
    except (Subscription.DoesNotExist, ValueError, ValidationError):
        return "missing"
    if str(subscription.user.telegram_id or "") != str(telegram_id):
        return "forbidden"
    subscription.delete()
    log.info("unsubscribed user=%s subscription=%s", subscription.user_id, subscription_id)
    return "removed"


def subscribers(request):
    """Users with a subscription to this exact category, place, and query.

    Parent categories, child categories, and broader places do not match.
    """
    country_id, city_id, category_id, query = listing_target(request)
    country_id, city_id = normalize_geo_ids(country_id, city_id)
    category_id = (category_id or "").strip() or None
    query = (query or "").strip()[:Subscription.QUERY_MAX_LENGTH]
    found = Subscription.objects.filter(
        country_id=country_id,
        city_id=city_id,
        category_id=category_id,
        query=query,
    ).select_related("user")
    if request.user.is_authenticated:
        found = found.exclude(user=request.user)
    return [subscription.user for subscription in found.order_by("user__full_name", "user__slug")]


def is_subscribed(user, country_id, city_id, category_id, query):
    if not user.is_authenticated:
        return False
    country_id, city_id = normalize_geo_ids(country_id, city_id)
    category_id = (category_id or "").strip() or None
    query = (query or "").strip()[:Subscription.QUERY_MAX_LENGTH]
    return Subscription.objects.filter(
        user=user,
        country_id=country_id,
        city_id=city_id,
        category_id=category_id,
        query=query,
    ).exists()


def listing_target(request):
    """Country, city, category and search the current listing is showing."""
    kwargs = request.resolver_match.kwargs if request.resolver_match else {}
    category_id = kwargs.get("subcategory") or kwargs.get("category") or ""
    return (
        getattr(request, "country_id", None) or EVERYWHERE,
        getattr(request, "city_id", None) or EVERYWHERE,
        category_id,
        request.GET.get("query") or "",
    )


def subscribers_for_item(item, subscription_ids=None):
    """One subscription per user who should hear about this new item.

    Overlapping subscriptions all match. The user still gets one message.
    Only members with a linked Telegram account.
    """
    geo = Q(country__isnull=True, city__isnull=True) | Q(country_id=item.country_id, city__isnull=True)
    if item.city_id:
        geo |= Q(country_id=item.country_id, city_id=item.city_id)
    if item.country_id == settings.ONLINE_COUNTRY_ID:
        geo |= Q(include_online=True)

    categories = Q(category__isnull=True)
    if item.subcategory_id:
        categories |= Q(category_id=item.subcategory_id) | Q(category_id=item.category_id)
    elif item.category_id:
        categories |= Q(category_id=item.category_id)

    now = timezone.now()
    candidates = (
        Subscription.objects
        .select_related("user", "country", "city", "category")
        .filter(geo, categories)
        .filter(user__membership_expires_at__gte=now)
        .filter(Q(user__membership_started_at__isnull=True) | Q(user__membership_started_at__lte=now))
        .filter(user__deleted_at__isnull=True)
        .exclude(user__telegram_id__isnull=True)
        .exclude(user__telegram_id="")
        .exclude(user_id=item.author_id)
    )

    if subscription_ids is not None:
        candidates = candidates.filter(id__in=subscription_ids)

    chosen = {}
    for subscription in candidates:
        if subscription.user.is_banned or subscription.user_id in chosen or not search.item_matches(item, subscription.query):
            continue
        chosen[subscription.user_id] = subscription
    return list(chosen.values())


def normalize_geo_ids(country_id, city_id):
    country_id = None if not country_id or country_id == EVERYWHERE else country_id
    city_id = None if not city_id or city_id == EVERYWHERE else city_id
    if city_id and not country_id:
        city_id = None
    return country_id, city_id
