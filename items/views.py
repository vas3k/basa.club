from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from categories.models import Category
from comments.forms import CommentForm
from comments.models import Comment, CommentVote
from items.models import Item


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

    return render(request, "index.html", {"items": items})


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

    return render(request, "index.html", {"items": items})


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

    comments = list(Comment.visible_objects().filter(item=item).order_by("created_at"))
    children = {}
    for comment in comments:
        children.setdefault(comment.reply_to_id, []).append(comment)

    def branch(parent_id):
        return [{"comment": comment, "replies": branch(comment.id)} for comment in children.get(parent_id, [])]

    item_voted = False
    voted_comments = set()
    if request.user.is_authenticated:
        item_voted = item.votes.filter(user=request.user).exists()
        voted_comments = set(
            CommentVote.objects.filter(user=request.user, comment__item=item).values_list("comment_id", flat=True)
        )

    return render(request, "items/page.html", {
        "item": item,
        "show_owner_actions": is_owner,
        "comments_tree": branch(None),
        "item_voted": item_voted,
        "voted_comments": voted_comments,
        "comment_form": CommentForm(item=item),
    })
