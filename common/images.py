import logging

import requests
from django.conf import settings

log = logging.getLogger(__name__)


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
