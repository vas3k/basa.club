import logging

import requests
from django.conf import settings

log = logging.getLogger(__name__)

IMAGE_KINDS = {
    "jpg": "jpeg",
    "jpeg": "jpeg",
    "png": "png",
    "gif": "gif",
    "webp": "webp",
}
IMAGE_CONTENT_TYPES = {
    "jpeg": {"image/jpeg", "image/jpg"},
    "png": {"image/png"},
    "gif": {"image/gif"},
    "webp": {"image/webp"},
}


def supported_image(filename, uploaded):
    extension = ""
    if filename and "." in filename:
        extension = filename.rsplit(".", 1)[-1].lower()
    kind = IMAGE_KINDS.get(extension)
    if not kind:
        return False

    content_type = (getattr(uploaded, "content_type", "") or "").split(";", 1)[0].strip().lower()
    allowed = IMAGE_CONTENT_TYPES[kind]
    if content_type and content_type not in allowed and content_type != "application/octet-stream":
        return False

    try:
        header = uploaded.read(16) or b""
    except OSError:
        return False
    try:
        uploaded.seek(0)
    except OSError:
        return False

    if kind == "jpeg":
        return header.startswith(b"\xff\xd8\xff")
    if kind == "png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if kind == "gif":
        return header.startswith((b"GIF87a", b"GIF89a"))
    return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"


def upload_image_multipart(filename, data):
    """Forward a file to Pepic and trust the returned media URL."""
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
    except requests.exceptions.RequestException:
        log.warning("Image upload request failed")
        return None

    if not 200 <= uploaded.status_code <= 299:
        log.warning("Image upload failed with status %s", uploaded.status_code)
        return None

    try:
        payload = uploaded.json()
        urls = payload.get("uploaded") if isinstance(payload, dict) else None
    except ValueError:
        log.warning("Image upload returned invalid JSON")
        return None

    if not isinstance(urls, list):
        return None

    url = urls[0] if urls else None
    if not isinstance(url, str) or not url:
        return None
    return url
