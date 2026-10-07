from django.contrib.auth.decorators import login_required
from django.db.models import F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from categories.models import Category
from common.pagination import paginate
from comments.forms import CommentForm, ReplyForm
from comments.models import Comment
from counters import counters
from common.contacts import CONTACT_EDITOR_FIELDS
from geo.models import GeoCountry
from items.forms import ItemForm
from items.models import Item
from notifications import notification
from notifications.models import Subscription
from notifications.subscriptions import subscribers
from users.flags import has_user_flag

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


def listing_queryset(request, items):
    if request.city_id != "everywhere":
        items = items.filter(
            Q(city_id=request.city_id)
            | Q(city__isnull=True, country_id=request.country_id)
            | Q(city__isnull=True, country__isnull=True)
        )
    elif request.country_id != "everywhere":
        items = items.filter(Q(country_id=request.country_id) | Q(country__isnull=True))

    query = (request.GET.get("query") or "").strip()
    if query and request.user.is_authenticated:
        items = items.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(location__icontains=query)
            | Q(promo_code__icontains=query)
        )

    if request.GET.get("hide_global"):
        items = items.exclude(country__isnull=True)

    sort = request.GET.get("sort")
    return items.order_by(*FEED_SORTS.get(sort, FEED_SORTS["standard"]))


def listing_feed_context(request, items):
    items = paginate(request, listing_queryset(request, items))
    sort = request.GET.get("sort")
    return {
        "items": items,
        "feed_sort": sort if sort in FEED_SORTS else "standard",
        "hide_global": request.GET.get("hide_global"),
        "subscribers": subscribers(request) if request.user.is_authenticated and items.paginator.count == 0 else [],
    }


def index_page(request, country=None):
    if response := anonymous_search_redirect(request):
        return response

    if country:
        country = get_object_or_404(GeoCountry, pk=country)
        request.country_id = country.id
        request.city_id = "everywhere"

    country_items = []
    if request.country_id != "everywhere":
        country_items = list(Item.objects_for_user(request.user).filter(
            country_id=request.country_id,
        ).order_by("-created_at")[:20])

    all_items = list(Item.objects_for_user(request.user).order_by("-created_at")[:10])

    subscriptions = []
    if request.user.is_authenticated:
        subscriptions = (
            Subscription.objects.filter(user=request.user)
            .select_related("country", "city", "category")
            .order_by("-created_at")
        )
        if request.country_id != "everywhere":
            subscriptions = subscriptions.exclude(
                country_id=request.country_id,
                city__isnull=True,
                category__isnull=True,
                query="",
            )
        subscriptions = list(subscriptions[:5])
        for subscription in subscriptions:
            items = Item.objects_for_user(request.user)
            if subscription.city_id:
                items = items.filter(
                    Q(city_id=subscription.city_id)
                    | Q(city__isnull=True, country_id=subscription.country_id)
                    | Q(city__isnull=True, country__isnull=True)
                )
            elif subscription.country_id:
                items = items.filter(Q(country_id=subscription.country_id) | Q(country__isnull=True))
            if subscription.category_id and subscription.category.parent_id:
                items = items.filter(subcategory_id=subscription.category_id)
            elif subscription.category_id:
                items = items.filter(category_id=subscription.category_id)
            if subscription.query:
                items = items.filter(
                    Q(title__icontains=subscription.query)
                    | Q(description__icontains=subscription.query)
                    | Q(location__icontains=subscription.query)
                    | Q(promo_code__icontains=subscription.query)
                )
            subscription.index_items = items.order_by("-created_at")[:10]

    response = render(request, "index.html", {
        "country_items": country_items,
        "all_items": all_items,
        "subscriptions": subscriptions,
        "show_welcome": show_welcome_block(request),
        "subscribers": subscribers(request) if request.user.is_authenticated and not country_items and not all_items and not subscriptions else [],
    })
    if country:
        max_age = 365 * 24 * 60 * 60
        response.set_cookie("country", request.country_id, max_age=max_age, samesite="Lax", path="/")
        response.set_cookie("city", "everywhere", max_age=max_age, samesite="Lax", path="/")
    return response


def show_welcome_block(request):
    if request.COOKIES.get("is_welcome_read"):
        return False
    return not has_user_flag(request.user, "is_welcome_read")


def listing_page(request, country, city, category=None, subcategory=None):
    if response := anonymous_search_redirect(request):
        return response

    if "country" not in request.COOKIES:
        request.country_id = country
        request.city_id = city

    if subcategory:
        get_object_or_404(Category, pk=subcategory, root_id=category)
    elif category:
        get_object_or_404(Category, pk=category, parent__isnull=True)

    items = Item.objects_for_user(request.user)
    if subcategory:
        items = items.filter(subcategory_id=subcategory)
    elif category:
        items = items.filter(category_id=category)

    return render(request, "listing.html", listing_feed_context(request, items))


def is_item_admin(user):
    return user.is_authenticated and user.is_moderator


def moderator_item_activity(item, limit=7):
    upvotes = item.votes.filter(user__isnull=False)
    bookmarks = item.bookmarks.all()
    flags = list(item.flags.select_related("user").order_by("-created_at"))
    return {
        "upvoters": [vote.user for vote in upvotes.select_related("user").order_by("-created_at")[:limit]],
        "upvote_count": upvotes.count(),
        "bookmarkers": [bookmark.user for bookmark in bookmarks.select_related("user").order_by("-created_at")[:limit]],
        "bookmark_count": bookmarks.count(),
        "flags": flags,
        "flag_count": len(flags),
    }


def render_item_page(request, item, *, comment_form=None, reply_form=None, status=200):
    is_owner = request.user.is_authenticated and request.user.pk == item.author_id
    is_admin = is_item_admin(request.user)

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

    return render(request, "items/show/default.html", {
        "item": item,
        "show_owner_actions": is_owner and not is_admin,
        "show_admin_actions": is_admin,
        "moderation": moderator_item_activity(item) if is_admin else None,
        "comments_tree": comments_tree,
        "comment_form": comment_form,
        "reply_form": reply_form,
    }, status=status)


def item_page(request, country, city, category, item_id, subcategory=None):
    if response := anonymous_search_redirect(request):
        return response

    try:
        item = Item.fetch(
            user=request.user,
            pk=item_id,
            category_id=category,
            subcategory_id=subcategory,
        )
    except Item.DoesNotExist:
        raise Http404()
    is_owner = request.user.is_authenticated and request.user.pk == item.author_id
    is_public = item.visibility in (Item.VISIBILITY_VISIBLE, Item.VISIBILITY_LINK_ONLY) and not item.is_expired
    if not is_public and not is_owner and not is_item_admin(request.user):
        raise Http404()

    Item.objects.filter(pk=item.pk).update(view_count=F("view_count") + 1)

    return render_item_page(request, item)


@login_required
@require_http_methods(["GET", "POST"])
def create_item(request):
    form = ItemForm(request.POST or None, initial={
        "country": request.country_id if request.country_id != "everywhere" else None,
        "city": request.city_id if request.city_id != "everywhere" else None,
    })

    if request.method == "POST" and form.is_valid():
        action = request.POST.get("action") or "publish"
        item = form.save(
            author=request.user,
            is_draft=action in {"draft", "preview"},
            commit=False,
        )
        item.save()
        if item.is_listed:
            counters.item_created(item)
            notification.item_created(item)
        if action == "draft":
            return redirect("user_profile", slug=request.user.slug)
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
        "form_title": "Добавить пост в Базу",
        "form_url": reverse("item_create"),
        "is_new": True,
        "countries_options": countries,
        "categories_options": categories,
        "contact_fields": CONTACT_EDITOR_FIELDS,
    })


def manageable_item(request, item_id):
    item = get_object_or_404(Item.objects.select_related("author"), pk=item_id)
    if item.author_id != request.user.pk and not is_item_admin(request.user):
        raise Http404()
    return item


@login_required
@require_http_methods(["GET", "POST"])
def edit_item(request, item_id):
    item = manageable_item(request, item_id)
    old = Item.objects.get(pk=item.pk)
    form = ItemForm(request.POST or None, instance=item)

    if request.method == "POST" and form.is_valid():
        action = request.POST.get("action") or "save"
        if action == "hide":
            item = form.save(is_draft=True, commit=False)
        elif action == "publish":
            item = form.save(is_draft=False, commit=False)
        elif action in {"draft", "preview"}:
            item = form.save(is_draft=True, commit=False)
        else:
            item = form.save(keep_visibility=True, commit=False)
        item.save()
        if old.is_listed and item.is_listed:
            counters.item_updated(item, old)
        elif old.is_listed:
            counters.item_hidden(old)
        elif item.is_listed:
            counters.item_created(item)
            notification.item_created(item)
        if action == "draft":
            return redirect("user_profile", slug=request.user.slug)
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
        "form_title": "Редактируем",
        "form_url": reverse("item_edit", args=[item.id]),
        "is_new": False,
        "countries_options": countries,
        "categories_options": categories,
        "contact_fields": CONTACT_EDITOR_FIELDS,
    })


@login_required
@require_POST
def hide_item(request, item_id):
    item = manageable_item(request, item_id)
    old = Item.objects.get(pk=item.pk)
    item.visibility = Item.VISIBILITY_DRAFT
    item.published_at = None
    item.save(update_fields=["visibility", "published_at", "updated_at"])
    if old.is_listed:
        counters.item_hidden(old)
    return redirect(item.get_absolute_url())


@login_required
@require_POST
def delete_item(request, item_id):
    item = manageable_item(request, item_id)
    was_listed = item.is_listed
    is_owner = item.author_id == request.user.pk
    item.delete(by=request.user)
    if was_listed:
        counters.item_hidden(item)
    if is_owner:
        return redirect("user_profile", slug=request.user.slug)
    return redirect("godmode_list_model", model_name="items")
