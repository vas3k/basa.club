import logging

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone

from categories.models import Category
from geo.models import GeoCity, GeoCountry
from notifications.models import Subscription

log = logging.getLogger(__name__)

EVERYWHERE = "everywhere"


class InvalidSubscription(LookupError):
    pass


def subscribe_to_geo(user, country_id, city_id):
    """Subscribe a user to new items in one country and city.

    country_id and city_id are geo primary keys, or "everywhere".
    """
    country_id, city_id = _geo_ids(country_id, city_id)
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
        user.pk,
        country_id,
        city_id,
    )
    return subscription


def toggle_subscription(user, country_id, city_id, category_id, query):
    """Create the listing subscription, or delete it if it already exists."""
    country, city, category, query = normalize_target(country_id, city_id, category_id, query)
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
        )
    except IntegrityError:
        return True
    return True


def unsubscribe(subscription_id, telegram_id):
    """Remove one subscription owned by this Telegram account.

    Returns "removed", "missing", or "forbidden". Other subscriptions stay.
    """
    try:
        subscription = Subscription.objects.select_related("user").get(pk=subscription_id)
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
    country_id, city_id = _geo_ids(country_id, city_id)
    category_id = (category_id or "").strip() or None
    query = _query(query)
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
    country_id, city_id = _geo_ids(country_id, city_id)
    category_id = (category_id or "").strip() or None
    query = _query(query)
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


def subscribers_for_item(item):
    """One subscription per user who should hear about this new item.

    Overlapping subscriptions all match. The user still gets one message.
    Only members with a linked Telegram account.
    """
    chosen = {}
    for subscription in _candidates(item):
        if subscription.user_id in chosen or not _query_matches(subscription, item):
            continue
        chosen[subscription.user_id] = subscription
    return list(chosen.values())


def subscription_kind(subscription):
    if subscription.query:
        return "query"
    if subscription.category_id:
        return "category"
    if subscription.city_id:
        return "city"
    if subscription.country_id:
        return "country"
    return "global"


def normalize_target(country_id, city_id, category_id, query):
    country = None
    city = None
    category = None
    country_id, city_id = _geo_ids(country_id, city_id)
    query = _query(query)

    if country_id:
        country = GeoCountry.objects.filter(pk=country_id).first()
        if not country:
            raise InvalidSubscription(country_id)
    if city_id:
        city = GeoCity.objects.filter(pk=city_id, country=country).first() if country else None
        if not city:
            raise InvalidSubscription(city_id)
    category_id = (category_id or "").strip()
    if category_id:
        category = Category.objects.filter(pk=category_id).first()
        if not category:
            raise InvalidSubscription(category_id)
    return country, city, category, query


def _geo_ids(country_id, city_id):
    country_id = None if not country_id or country_id == EVERYWHERE else country_id
    city_id = None if not city_id or city_id == EVERYWHERE else city_id
    if city_id and not country_id:
        city_id = None
    return country_id, city_id


def _query(query):
    return (query or "").strip()[:Subscription.QUERY_MAX_LENGTH]


def _candidates(item):
    geo = Q(country__isnull=True, city__isnull=True)
    if item.country_id and item.city_id:
        geo |= Q(country_id=item.country_id, city__isnull=True)
        geo |= Q(city_id=item.city_id)
    elif item.country_id:
        # A country-wide item is shown on every city page of that country.
        geo |= Q(country_id=item.country_id)
    else:
        # A worldwide item is shown on every listing.
        geo = Q()

    categories = Q(category__isnull=True)
    if item.category_id:
        categories |= Q(category_id=item.category_id)
    if item.subcategory_id:
        categories |= Q(category_id=item.subcategory_id)

    now = timezone.now()
    return (
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


def _query_matches(subscription, item):
    needle = (subscription.query or "").strip().lower()
    if not needle:
        return True
    haystack = "\n".join((
        item.title or "",
        item.description or "",
        item.location or "",
        item.promo_code or "",
    )).lower()
    return needle in haystack
