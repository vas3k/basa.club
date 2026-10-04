import json

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from authn.decorators import api_login_required
from common.request import parse_ip_address, parse_useragent
from complaints.models import Flag
from items.models import Item


@api_login_required
@require_POST
def flag_item(request, item_id):
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Некорректный запрос"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "Некорректный запрос"}, status=400)

    reason = str(payload.get("reason") or "").strip()
    comment = str(payload.get("comment") or "").strip()
    if reason not in dict(Flag.REASONS):
        return JsonResponse({"error": "Выберите причину"}, status=400)
    if len(comment) > Flag.COMMENT_MAX_LENGTH:
        return JsonResponse({"error": "Комментарий слишком длинный"}, status=400)

    item = get_object_or_404(Item, pk=item_id)
    if item.visibility == Item.VISIBILITY_DRAFT and item.author_id != request.user.pk:
        raise Http404()

    Flag.objects.create(
        user=request.user,
        item=item,
        reason=reason,
        comment=comment,
        ipaddress=parse_ip_address(request),
        useragent=parse_useragent(request),
    )
    return JsonResponse({"ok": True})
