from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from authn.helpers import api_login_required
from common.images import upload_image_multipart


@api_login_required
@require_POST
def upload_image(request):
    upload = request.FILES.get("media")
    if not upload:
        return JsonResponse({"error": "Выберите файл"}, status=400)

    if not settings.MEDIA_UPLOAD_CODE:
        return JsonResponse({"error": "Загрузка картинок не настроена"}, status=503)
    url = upload_image_multipart(upload.name, upload)
    if not url:
        return JsonResponse({"error": "Не получилось загрузить картинку"}, status=502)
    return JsonResponse({"url": url})
