import logging
from copy import copy

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from categories.models import Category
from common.ai.item_parser import ItemParsingError, parse_item
from common.pagination import paginate
from comments.forms import CommentForm, ReplyForm
from comments.models import Comment
from counters import counters
from common.contacts import CONTACT_EDITOR_FIELDS
from geo.models import GeoCity, GeoCountry
from items.forms import AIItemForm, ItemForm
from items.models import Item
from notifications import notification
from search import search
from notifications.models import Subscription
from notifications.subscriptions import subscribers

log = logging.getLogger(__name__)

FEED_SORTS = {
    "standard": ("-created_at",),
    "date": ("-published_at", "-created_at"),
    "rating": ("-rating", "-created_at"),
}


def anonymous_search_redirect(request):
    """Text search looks through private fields, so guests are sent to login."""
    if request.user.is_authenticated:
        return None
    if (request.GET.get("query") or "").strip():
        return redirect("login")
    return None


def main_index_page(request):
    if response := anonymous_search_redirect(request):
        return response

    query = (request.GET.get("query") or "").strip()[:200]
    feed = search.filter_items(
        Item.objects_for_user(request.user, Item.visible_objects()), query,
    ).order_by("-published_at", "-id")
    all_items = paginate(request, feed)
    shown_ids = [item.id for item in all_items]

    subscriptions = []
    if request.user.is_authenticated:
        subscriptions = list(
            Subscription.objects.filter(user=request.user)
            .select_related("country", "city", "category").order_by("-created_at")
        )
        for subscription in subscriptions:
            items = feed.exclude(id__in=shown_ids)
            if subscription.country_id:
                place = Q(country_id=subscription.country_id)
                if subscription.city_id:
                    place &= Q(city_id=subscription.city_id)
                if subscription.include_online:
                    place |= Q(country_id=settings.ONLINE_COUNTRY_ID)
                items = items.filter(place)
            if subscription.category_id and subscription.category.parent_id:
                items = items.filter(subcategory_id=subscription.category_id)
            elif subscription.category_id:
                items = items.filter(category_id=subscription.category_id)
            if subscription.query:
                items = search.filter_items(items, subscription.query)
            subscription.index_items = list(items[:10])
            shown_ids.extend(item.id for item in subscription.index_items)

    return render(request, "index/main.html", {
        "all_items": all_items,
        "subscriptions": subscriptions,
        "subscribers": subscribers(request) if request.user.is_authenticated and not all_items else [],
    })


def country_index_page(request, country):
    if response := anonymous_search_redirect(request):
        return response

    country = get_object_or_404(GeoCountry, id=country)
    request.country_id = country.id
    request.city_id = "everywhere"

    query = (request.GET.get("query") or "").strip()[:200]
    feed = search.filter_items(
        Item.objects_for_user(request.user, Item.visible_objects()), query,
    ).filter(country=country).order_by("-published_at", "-id")
    country_items = list(feed[:20])
    shown_ids = [item.id for item in country_items]

    city_blocks = []
    city_counts = dict(
        feed.exclude(city_id=None).order_by().values("city_id").annotate(total=Count("id"))
        .values_list("city_id", "total")
    )
    for city in GeoCity.objects.filter(country=country, id__in=city_counts):
        city_items = list(feed.filter(city=city).exclude(id__in=shown_ids)[:10])
        city_blocks.append({
            "city": city,
            "count": city_counts[city.id],
            "items": city_items,
        })

    return render(request, "index/country.html", {
        "country_items": country_items,
        "city_blocks": city_blocks,
        "subscribers": subscribers(request) if request.user.is_authenticated and not country_items else [],
    })


def listing_page(request, country, city, category=None, subcategory=None):
    if response := anonymous_search_redirect(request):
        return response

    request.country_id = country
    request.city_id = city
    if country == "everywhere" and city != "everywhere":
        raise Http404()

    current_category = None
    if subcategory:
        current_category = get_object_or_404(Category, id=subcategory, root_id=category)
    elif category:
        current_category = get_object_or_404(Category, id=category, parent__isnull=True)

    items = Item.objects_for_user(request.user, Item.visible_objects())
    if subcategory:
        items = items.filter(subcategory_id=subcategory)
    elif category:
        items = items.filter(category_id=category)

    include_online = False
    if current_category:
        root = current_category.root or current_category
        include_online = current_category.metadata.get("include_online", root.metadata.get("include_online", False))
    include_online_param = request.GET.get(settings.INCLUDE_ONLINE_PARAM)
    if include_online_param in {"0", "1"}:
        include_online = include_online_param == "1"
    request.include_online = include_online
    if country != "everywhere":
        get_object_or_404(GeoCountry, id=country)
        here = Q(country_id=country)
        if city != "everywhere":
            get_object_or_404(GeoCity, id=city, country_id=country)
            here &= Q(city_id=city)
        if include_online:
            here |= Q(country_id=settings.ONLINE_COUNTRY_ID)
        items = items.filter(here)

    query = (request.GET.get("query") or "").strip()[:200]
    items = search.filter_items(items, query)

    sort = request.GET.get("sort")
    ordering = list(FEED_SORTS.get(sort, FEED_SORTS["standard"]))
    if query and sort not in {"date", "rating"}:
        ordering = ["-search_rank", *ordering]
    items = paginate(request, items.order_by(*ordering))

    return render(request, "listing.html", {
        "items": items,
        "feed_sort": sort if sort in FEED_SORTS else "standard",
        "include_online": include_online,
        "include_online_param": include_online_param if include_online_param in {"0", "1"} else None,
        "subscribers": subscribers(request) if request.user.is_authenticated and items.paginator.count == 0 else [],
    })


def render_item_page(request, item, *, comment_form=None, reply_form=None, status=200):
    is_owner = request.user.is_authenticated and request.user.id == item.author_id
    is_admin = request.user.is_authenticated and request.user.is_moderator

    comments_tree = []
    if request.user.is_authenticated:
        comments = Comment.objects_for_user(request.user).filter(item=item).order_by("created_at")
        replies = {}
        for comment in comments:
            if comment.reply_to_id:
                replies.setdefault(comment.reply_to_id, []).append(comment)

        comments_tree = [
            {"comment": comment, "replies": replies.get(comment.id, [])}
            for comment in comments
            if not comment.reply_to_id
        ]
        comment_form = comment_form or CommentForm(item=item)
        reply_form = reply_form or ReplyForm(item=item)

    moderation = None
    if is_admin:
        upvotes = item.votes.filter(user__isnull=False)
        bookmarks = item.bookmarks.all()
        flags = list(item.flags.select_related("user").order_by("-created_at"))
        moderation = {
            "upvoters": [vote.user for vote in upvotes.select_related("user").order_by("-created_at")[:7]],
            "upvote_count": upvotes.count(),
            "bookmarkers": [bookmark.user for bookmark in bookmarks.select_related("user").order_by("-created_at")[:7]],
            "bookmark_count": bookmarks.count(),
            "flags": flags,
            "flag_count": len(flags),
        }

    return render(request, "items/show/default.html", {
        "item": item,
        "show_owner_actions": is_owner and not is_admin,
        "show_admin_actions": is_admin,
        "moderation": moderation,
        "comments_tree": comments_tree,
        "comment_form": comment_form,
        "reply_form": reply_form,
    }, status=status)


def item_page(request, country, city, category, item_id, subcategory=None):
    if response := anonymous_search_redirect(request):
        return response

    item = get_object_or_404(
        Item.objects_for_user(request.user),
        id=item_id,
        category_id=category,
        subcategory_id=subcategory,
    )

    Item.objects.filter(id=item.id).update(view_count=F("view_count") + 1)

    request.country_id = item.country_id
    request.city_id = item.city_id or "everywhere"
    return render_item_page(request, item)


@login_required
@require_http_methods(["GET", "POST"])
def compose_item_ai(request):
    if request.method == "GET":
        error = request.session.pop("item_ai_error", None)
        if error:
            return render(request, "error.html", {
                "title": "Не получилось разобрать пост",
                "message": error,
            }, status=400)

    form = AIItemForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            fields = parse_item(form.cleaned_data["text"], request.user)
            request.session["item_ai_initial"] = {
                name.removesuffix("_id"): value for name, value in fields.items()
            }
            return redirect(reverse("item_create") + "?prefill_from_session=1")
        except ItemParsingError as error:
            request.session["item_ai_error"] = str(error)
        except Exception:
            log.exception("Web item parse failed")
            request.session["item_ai_error"] = "Не получилось разобрать сообщение. Попробуйте ещё раз."
        return redirect("item_create_ai")

    return render(request, "items/compose/ai.html", {
        "form": form,
        "form_title": "Добавить пост в Базу",
        "form_url": reverse("item_create_ai"),
    })


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def compose_item(request, item_id=None):
    item = Item(author=request.user, visibility=Item.VISIBILITY_DRAFT)
    if item_id:
        item = get_object_or_404(Item.objects.select_for_update(), id=item_id)
        if item.author_id != request.user.id and not request.user.is_moderator:
            raise Http404()
    old = copy(item)

    initial = {}
    if not item_id:
        country = GeoCountry.objects.filter(name=request.user.country).first() if request.user.country else None
        city = GeoCity.objects.filter(country=country, name=request.user.city).first() if country and request.user.city else None
        initial = {"country": country.id if country else "", "city": city.id if city else None}
        if request.method == "GET" and request.GET.get("prefill_from_session") == "1":
            initial.update(request.session.pop("item_ai_initial", {}))
        initial = ItemForm.initial_from_query(request.GET, initial)
    form = ItemForm(request.POST if request.method == "POST" else None, instance=item, initial=initial)

    action = request.POST.get("action", "save")
    publishing = old.visibility == Item.VISIBILITY_DRAFT and action == "publish"
    first_publication = publishing and not old.published_at
    if request.method == "POST" and form.is_valid():
        if first_publication and not Item.check_rate_limits(item.author):
            form.add_error(None, f"Можно опубликовать не больше {settings.ITEM_RATE_LIMIT} постов за сутки")
        else:
            item = form.save(commit=False)
            if publishing:
                item.visibility = Item.VISIBILITY_VISIBLE
                item.moderator_comment = None
                if first_publication:
                    item.published_at = timezone.now()
            elif old.visibility != Item.VISIBILITY_DRAFT:
                item.updated_at = timezone.now()
            item.save()

            search.update_item_index(item)
            if old.is_listed and item.is_listed:
                counters.item_updated(item, old)
            elif old.is_listed:
                counters.item_hidden(old)
            elif item.is_listed:
                counters.item_created(item)
            if first_publication:
                transaction.on_commit(lambda: notification.item_created(item))

            if action == "draft":
                return redirect("user_profile", slug=item.author.slug)
            return redirect(item.get_absolute_url())

    countries = [
        {
            "id": country.id,
            "name": country.name,
            "icon": country.icon,
            "cities": [{"id": city.id, "name": city.name, "icon": city.icon} for city in country.cities.all()],
        }
        for country in GeoCountry.objects.prefetch_related("cities")
    ]
    categories = [
        {
            "id": category.id,
            "name": category.name,
            "icon": category.icon,
            "children": [{"id": child.id, "name": child.name} for child in category.children.all()],
        }
        for category in Category.objects.filter(parent__isnull=True).prefetch_related("children")
    ]

    return render(request, "items/compose/default.html", {
        "form": form,
        "form_title": "Редактируем" if item_id else "Добавить пост в Базу",
        "form_url": reverse("item_edit", args=[item_id]) if item_id else reverse("item_create"),
        "is_new": not item_id,
        "countries_options": countries,
        "categories_options": categories,
        "contact_fields": CONTACT_EDITOR_FIELDS,
    })


@login_required
@require_POST
def hide_item(request, item_id):
    item = get_object_or_404(Item.objects.select_related("author"), id=item_id)
    if item.author_id != request.user.id and not (request.user.is_authenticated and request.user.is_moderator):
        raise Http404()
    old = Item.objects.get(id=item.id)
    item.visibility = Item.VISIBILITY_DRAFT
    item.save(update_fields=["visibility"])
    search.update_item_index(item)
    if old.is_listed:
        counters.item_hidden(old)
    return redirect(item.get_absolute_url())


@login_required
@require_POST
def delete_item(request, item_id):
    item = get_object_or_404(Item.objects.select_related("author"), id=item_id)
    if item.author_id != request.user.id and not (request.user.is_authenticated and request.user.is_moderator):
        raise Http404()
    was_listed = item.is_listed
    is_owner = item.author_id == request.user.id
    item.delete(by=request.user)
    search.delete_item_index(item)
    if was_listed:
        counters.item_hidden(item)
    if is_owner:
        return redirect("user_profile", slug=request.user.slug)
    return redirect("godmode_list_model", model_name="items")
