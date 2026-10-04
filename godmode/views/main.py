from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from godmode.config import ADMIN, ITEMS_PER_PAGE
from godmode.filters import FILTER_OPERATORS, apply_filters, get_filterable_fields
from users.models import User
from vas3k_base.exceptions import AccessDenied


def admin_queryset(model):
    if hasattr(model, "all_objects"):
        return model.all_objects.all()
    return model.objects.all()


def ensure_access(request):
    if not ADMIN.has_access(request.user):
        raise AccessDenied(
            title="Вам сюда нельзя",
            message="Админка доступна только администраторам",
        )


@login_required
def godmode(request):
    ensure_access(request)
    return render(request, "godmode/layout.html", {
        "admin": ADMIN,
    })


@login_required
def godmode_list_model(request, model_name):
    ensure_access(request)

    admin_model = ADMIN.get_model(model_name)
    if not admin_model or not admin_model.model:
        raise Http404()

    if not admin_model.has_list_access(request.user):
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "Вам сюда нельзя",
            "message": f"Раздел «{admin_model.title}» доступен только администраторам.",
        })

    page = request.GET.get("page", 1)
    filter_field = request.GET.get("filter_field", "")
    filter_operator = request.GET.get("filter_operator", "")
    filter_value = request.GET.get("filter_value", "")
    sort_field = request.GET.get("sort_field", "")
    sort_direction = request.GET.get("sort_direction", "")

    queryset = apply_filters(
        admin_queryset(admin_model.model),
        admin_model.model,
        filter_field,
        filter_operator,
        filter_value,
        sort_field,
        sort_direction,
    )
    if not queryset.ordered:
        queryset = queryset.order_by("pk")
    paginator = Paginator(queryset, ITEMS_PER_PAGE)
    try:
        page_obj = paginator.page(page)
    except Exception:
        page_obj = paginator.page(1)

    return render(request, "godmode/list.html", {
        "admin": ADMIN,
        "admin_model": admin_model,
        "columns": admin_model.get_list_fields(),
        "items": page_obj,
        "filters": get_filterable_fields(admin_model.model),
        "filter_operators": FILTER_OPERATORS,
        "current_filters": {
            "field": filter_field,
            "operator": filter_operator,
            "value": filter_value,
        },
        "current_sort": {
            "field": sort_field,
            "direction": sort_direction,
        },
        "primary_key_field": admin_model.model._meta.pk.name,
        "show_create_button": admin_model.has_create_access(request.user),
    })


@login_required
def godmode_edit_model(request, model_name, item_id):
    ensure_access(request)

    admin_model = ADMIN.get_model(model_name)
    if not admin_model or not admin_model.model:
        raise Http404()

    can_edit = admin_model.has_edit_access(request.user)
    actions = admin_model.actions_for(request.user)
    if not can_edit and not actions:
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "Вам сюда нельзя",
            "message": f"Редактировать «{admin_model.title}» могут только администраторы.",
        })

    primary_key_field = admin_model.model._meta.pk.name
    item = get_object_or_404(admin_queryset(admin_model.model), **{primary_key_field: item_id})
    edit_form_class = admin_model.get_form_class()

    if request.method == "POST":
        if not can_edit:
            return render(request, "godmode/message.html", {
                "admin": ADMIN,
                "title": "Вам сюда нельзя",
                "message": f"Редактировать «{admin_model.title}» могут только администраторы.",
            })
        form = edit_form_class(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect("godmode_list_model", model_name=model_name)
    else:
        form = edit_form_class(instance=item)

    return render(request, "godmode/edit.html", {
        "admin": ADMIN,
        "admin_model": admin_model,
        "item": item,
        "form": form,
        "actions": actions,
        "primary_key_field": primary_key_field,
        "show_edit_form": can_edit,
        "show_delete_button": admin_model.has_delete_access(request.user),
    })


@login_required
def godmode_delete_model(request, model_name, item_id):
    ensure_access(request)

    admin_model = ADMIN.get_model(model_name)
    if not admin_model or not admin_model.model:
        raise Http404()

    if not admin_model.has_delete_access(request.user):
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "Вам сюда нельзя",
            "message": "Пользователей нельзя удалять из базы." if admin_model.model is User else f"Удалять из «{admin_model.title}» могут только администраторы.",
        })

    primary_key_field = admin_model.model._meta.pk.name
    item = get_object_or_404(admin_queryset(admin_model.model), **{primary_key_field: item_id})

    if request.method != "POST":
        return render(request, "godmode/confirm.html", {
            "admin": ADMIN,
            "title": f"Удалить {admin_model.title}: {item_id}?",
            "message": "Для записей и комментариев это мягкое удаление",
            "button": "Да, удаляем",
        })

    item.delete()
    return redirect("godmode_list_model", model_name=model_name)


@login_required
def godmode_create_model(request, model_name):
    ensure_access(request)

    admin_model = ADMIN.get_model(model_name)
    if not admin_model or not admin_model.model:
        raise Http404()

    if not admin_model.has_create_access(request.user):
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "Вам сюда нельзя",
            "message": f"Создавать записи в «{admin_model.title}» могут только администраторы.",
        })

    create_form_class = admin_model.get_form_class()
    if request.method == "POST":
        form = create_form_class(request.POST)
        if form.is_valid():
            form.save()
            return redirect("godmode_list_model", model_name=model_name)
    else:
        form = create_form_class()

    return render(request, "godmode/create.html", {
        "admin": ADMIN,
        "admin_model": admin_model,
        "form": form,
    })


@login_required
def godmode_show_page(request, page_name):
    ensure_access(request)

    admin_page = ADMIN.get_page(page_name)
    if not admin_page:
        raise Http404()

    if not admin_page.has_access(request.user):
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "Вам сюда нельзя",
            "message": f"Страница «{admin_page.title}» доступна только администраторам.",
        })

    if not admin_page.view:
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "Страницу ещё не сделали",
            "message": "У страницы нет view",
        })

    return render(request, "godmode/page.html", {
        "admin": ADMIN,
        "admin_page": admin_page,
        "page": admin_page.view(request, admin_page),
    })


@login_required
def godmode_action(request, model_name, item_id, action_code):
    ensure_access(request)

    admin_model = ADMIN.get_model(model_name)
    if not admin_model or not admin_model.model:
        raise Http404()

    admin_action = admin_model.actions.get(action_code)
    if not admin_action:
        raise Http404()

    if not admin_action.has_access(request.user):
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "Вам сюда нельзя",
            "message": f"Действие «{admin_action.title}» доступно только администраторам.",
        })

    primary_key_field = admin_model.model._meta.pk.name
    item = get_object_or_404(admin_queryset(admin_model.model), **{primary_key_field: item_id})
    context = dict(
        admin=ADMIN,
        admin_model=admin_model,
        admin_action=admin_action,
    )
    if request.method == "GET" and admin_action.get:
        return admin_action.get(request, item, **context)
    if request.method == "POST" and admin_action.post:
        return admin_action.post(request, item, **context)
    raise Http404()
