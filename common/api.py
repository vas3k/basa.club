from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from common.images import IMAGE_EXTENSIONS, IMAGE_MAX_BYTES, IMAGE_TYPES, upload_image_multipart


@require_POST
def upload_image(request):
    upload = request.FILES.get("media")
    if not upload:
        return JsonResponse({"error": "Выберите файл"}, status=400)
    if upload.size > IMAGE_MAX_BYTES:
        return JsonResponse({"error": "Файл больше 15 МБ"}, status=400)

    extension = Path(upload.name or "").suffix.lower()
    if upload.content_type not in IMAGE_TYPES and extension not in IMAGE_EXTENSIONS:
        return JsonResponse({"error": "Можно загрузить jpeg, png, bmp или webp"}, status=400)
    if not settings.MEDIA_UPLOAD_CODE:
        return JsonResponse({"error": "Загрузка картинок не настроена"}, status=503)

    url = upload_image_multipart(upload.name, upload)
    if not url:
        return JsonResponse({"error": "Не получилось загрузить картинку"}, status=502)
    return JsonResponse({"url": url})
