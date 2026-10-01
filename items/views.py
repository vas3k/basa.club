from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from categories.models import Category
from comments.forms import CommentForm, ReplyForm
from comments.models import Comment, CommentVote
from geo.models import GeoCountry
from items.forms import ItemForm
from items.models import Item, ItemVote


def index_page(request):
    items = Item.visible_objects()
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
        items = items.filter(Q(title__icontains=query) | Q(description__icontains=query))

    return render(request, "index.html", {
        "items": items,
        "voted_items": ItemVote.voted_item_ids(request.user, items),
    })


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
        items = items.filter(Q(title__icontains=query) | Q(description__icontains=query))

    return render(request, "index.html", {
        "items": items,
        "voted_items": ItemVote.voted_item_ids(request.user, items),
    })


def render_item_page(request, item, *, comment_form=None, reply_form=None, status=200):
    is_owner = request.user.is_authenticated and request.user.pk == item.author_id

    comments = Comment.objects.filter(item=item).select_related("author").order_by("created_at")
    replies = {}
    for comment in comments:
        if comment.reply_to_id and not comment.is_deleted():
            replies.setdefault(comment.reply_to_id, []).append(comment)

    # deleted comments stay as a placeholder only if somebody replied to them
    comments_tree = [
        {"comment": comment, "replies": replies.get(comment.id, [])}
        for comment in comments
        if not comment.reply_to_id and (not comment.is_deleted() or comment.id in replies)
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


def item_page(request, country, city, category, subcategory, item_id):
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
        item = form.save(author=request.user, is_draft=request.POST.get("action") == "draft")
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
    })


@login_required
@require_http_methods(["GET", "POST"])
def edit_item(request, item_id):
    item = get_object_or_404(Item, pk=item_id, author=request.user)
    form = ItemForm(request.POST or None, instance=item)

    if request.method == "POST" and form.is_valid():
        item = form.save(is_draft=request.POST.get("action") == "draft")
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
    })


@login_required
@require_POST
def hide_item(request, item_id):
    item = get_object_or_404(Item, pk=item_id, author=request.user)
    item.visibility = Item.VISIBILITY_DRAFT
    item.published_at = None
    item.save(update_fields=["visibility", "published_at", "updated_at"])
    return redirect(item.get_absolute_url())


@login_required
@require_POST
def delete_item(request, item_id):
    item = get_object_or_404(Item, pk=item_id, author=request.user)
    item.delete()
    return redirect("user_profile", slug="me")
