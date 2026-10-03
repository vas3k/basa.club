from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from categories.models import Category
from common.pagination import paginate
from comments.forms import CommentForm, ReplyForm
from comments.models import Comment, CommentVote
from common import counters
from common.contacts import CONTACT_EDITOR_FIELDS
from geo.models import GeoCountry
from items.forms import ItemForm
from items.models import Item, ItemVote
import notifications

FEED_SORTS = {
    "standard": ("-created_at",),
    "date": ("-published_at", "-created_at"),
    "rating": ("-rating", "-created_at"),
}


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
    if query:
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
        "voted_items": ItemVote.voted_item_ids(request.user, items.object_list),
        "feed_sort": sort if sort in FEED_SORTS else "standard",
        "hide_global": request.GET.get("hide_global"),
    }


def index_page(request):
    return render(request, "index.html", listing_feed_context(request, Item.visible_objects()))


def listing_page(request, country, city, category=None, subcategory=None):
    if "country" not in request.COOKIES:
        request.country_id = country
        request.city_id = city

    if subcategory:
        get_object_or_404(Category, pk=subcategory, root_id=category)
    elif category:
        get_object_or_404(Category, pk=category, parent__isnull=True)

    items = Item.visible_objects()
    if subcategory:
        items = items.filter(subcategory_id=subcategory)
    elif category:
        items = items.filter(category_id=category)

    return render(request, "index.html", listing_feed_context(request, items))


def render_item_page(request, item, *, comment_form=None, reply_form=None, status=200):
    is_owner = request.user.is_authenticated and request.user.pk == item.author_id

    comments = Comment.objects.filter(item=item).select_related("author").order_by("created_at")
    replies = {}
    for comment in comments:
        if comment.reply_to_id:
            replies.setdefault(comment.reply_to_id, []).append(comment)

    comments_tree = [
        {"comment": comment, "replies": replies.get(comment.id, [])}
        for comment in comments
        if not comment.reply_to_id
    ]

    voted_comments = set()
    if request.user.is_authenticated:
        voted_comments = set(
            CommentVote.objects.filter(user=request.user, comment__item=item).values_list("comment_id", flat=True)
        )

    return render(request, "items/show/default.html", {
        "item": item,
        "show_owner_actions": is_owner,
        "comments_tree": comments_tree,
        "voted_items": ItemVote.voted_item_ids(request.user, [item]),
        "voted_comments": voted_comments,
        "comment_form": comment_form or CommentForm(item=item),
        "reply_form": reply_form or ReplyForm(item=item),
    }, status=status)


def item_page(request, country, city, category, item_id, subcategory=None):
    try:
        item = Item.fetch(
            pk=item_id,
            category_id=category,
            subcategory_id=subcategory,
        )
    except Item.DoesNotExist:
        raise Http404()
    is_owner = request.user.is_authenticated and request.user.pk == item.author_id
    is_public = item.visibility in (Item.VISIBILITY_VISIBLE, Item.VISIBILITY_LINK_ONLY) and not item.is_expired
    if not is_public and not is_owner:
        raise Http404()

    return render_item_page(request, item)


@login_required
@require_http_methods(["GET", "POST"])
def create_item(request):
    form = ItemForm(request.POST or None, initial={
        "country": request.country_id if request.country_id != "everywhere" else None,
        "city": request.city_id if request.city_id != "everywhere" else None,
    })

    if request.method == "POST" and form.is_valid():
        item = form.save(
            author=request.user,
            is_draft=request.POST.get("action") == "draft",
            commit=False,
        )
        item.save()
        if item.is_listed:
            counters.item_created(item)
            notifications.item_created(item)
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
        "form_title": "Добавить объявление",
        "form_url": reverse("item_create"),
        "countries_options": countries,
        "categories_options": categories,
        "contact_fields": CONTACT_EDITOR_FIELDS,
    })


@login_required
@require_http_methods(["GET", "POST"])
def edit_item(request, item_id):
    item = get_object_or_404(Item, pk=item_id, author=request.user)
    old = Item.objects.get(pk=item.pk)
    form = ItemForm(request.POST or None, instance=item)

    if request.method == "POST" and form.is_valid():
        item = form.save(is_draft=request.POST.get("action") == "draft", commit=False)
        item.save()
        if old.is_listed and item.is_listed:
            counters.item_updated(item, old)
        elif old.is_listed:
            counters.item_hidden(old)
        elif item.is_listed:
            counters.item_created(item)
            notifications.item_created(item)
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
        "form_title": "Редактировать объявление",
        "form_url": reverse("item_edit", args=[item.id]),
        "countries_options": countries,
        "categories_options": categories,
        "contact_fields": CONTACT_EDITOR_FIELDS,
    })


@login_required
@require_POST
def hide_item(request, item_id):
    item = get_object_or_404(Item, pk=item_id, author=request.user)
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
    item = get_object_or_404(Item.objects.select_related("author"), pk=item_id, author=request.user)
    was_listed = item.is_listed
    item.delete(by=request.user)
    if was_listed:
        counters.item_hidden(item)
    return redirect("user_profile", slug="me")
