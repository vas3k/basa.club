from django.conf import settings
from django.core.cache import caches
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from common.images import supported_image, upload_image_multipart
from common.request import parse_ip_address


@require_POST
def upload_image(request):
    if request.user.is_authenticated and request.user.is_banned:
        return JsonResponse({"error": "Аккаунт заблокирован"}, status=403)

    upload = request.FILES.get("media")
    if not upload:
        return JsonResponse({"error": "Выберите файл"}, status=400)
    if upload.size > 10 * 1024 * 1024:
        return JsonResponse({"error": "Картинка должна быть не больше 10 МБ"}, status=400)
    if not supported_image(upload.name, upload):
        return JsonResponse({"error": "Можно загрузить только картинки JPG, PNG, GIF или WebP"}, status=400)

    if not settings.MEDIA_UPLOAD_CODE:
        return JsonResponse({"error": "Загрузка картинок не настроена"}, status=503)
    if not request.user.is_authenticated:
        cache = caches["default" if settings.DEBUG else "redis_cache"]
        if not cache.add(f"anonymous-image-upload:{parse_ip_address(request)}", True, timeout=10):
            return JsonResponse({"error": "Подождите 10 секунд перед следующей загрузкой"}, status=429)

    url = upload_image_multipart(upload.name, upload)
    if not url:
        return JsonResponse({"error": "Не получилось загрузить картинку"}, status=502)
    return JsonResponse({"url": url})
