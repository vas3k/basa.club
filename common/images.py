import logging
from urllib.parse import urlparse

import requests
from django.conf import settings

log = logging.getLogger(__name__)

IMAGE_HOST = "i.vas3k.club"
IMAGE_MAX_COUNT = 10
IMAGE_MAX_BYTES = 15 * 1024 * 1024
IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/bmp",
    "image/x-ms-bmp",
    "image/webp",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def is_hosted_image(url):
    if not isinstance(url, str):
        return False
    parsed = urlparse(url.strip())
    return parsed.scheme == "https" and parsed.hostname == IMAGE_HOST and bool(parsed.path.strip("/"))


def upload_image_multipart(filename, data):
    """Upload one file to i.vas3k.club and return its URL."""
    if not data or not settings.MEDIA_UPLOAD_URL or not settings.MEDIA_UPLOAD_CODE:
        return None

    try:
        uploaded = requests.post(
            url=settings.MEDIA_UPLOAD_URL,
            params={"code": settings.MEDIA_UPLOAD_CODE},
            files={"media": (filename or "image", data)},
            headers={"Accept": "application/json"},
            timeout=60,
        )
    except requests.exceptions.RequestException as ex:
        log.error("Image upload error: %s", ex)
        return None

    if not 200 <= uploaded.status_code <= 299:
        log.error("Image upload error: %s %s", uploaded.status_code, uploaded.text[:300])
        return None

    try:
        urls = uploaded.json().get("uploaded") or []
    except ValueError as ex:
        log.error("Image upload error: %s", ex)
        return None

    url = urls[0] if urls else None
    if not is_hosted_image(url):
        return None
    return url
