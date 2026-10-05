import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from authn.decorators import api_login_required
from users.flags import ALLOWED_USER_FLAGS, set_user_flag


@api_login_required
@require_POST
def update_user_flag(request):
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Некорректный запрос"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "Некорректный запрос"}, status=400)

    flag = payload.get("flag")
    if flag not in ALLOWED_USER_FLAGS:
        return JsonResponse({"error": "Неизвестный флаг"}, status=400)

    value = payload.get("value")
    if not isinstance(value, bool):
        return JsonResponse({"error": "Флаг должен быть да или нет"}, status=400)

    set_user_flag(request.user, flag, value)
    return JsonResponse({"flag": flag, "value": value})
