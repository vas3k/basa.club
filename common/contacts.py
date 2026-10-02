import re

# Stored on an item as a list of {"type", "text", "comment"}.
# "custom" is a free-form contact: text and an optional comment, shown with a link icon.

CONTACT_MAX_LENGTH = 128
CONTACT_MAX_COUNT = 100

CONTACTS = [
    {"type": "phone", "label": "Телефон", "icon": "📞"},
    {"type": "telegram", "label": "Телеграм", "icon": "✈️"},
    {"type": "whatsapp", "label": "WhatsApp", "icon": "💬"},
    {"type": "website", "label": "Сайт", "icon": "🌐"},
    {"type": "custom", "label": "Другое", "icon": "🔗"},
]

CONTACT_TYPES = {item["type"] for item in CONTACTS}
CONTACT_EDITOR_FIELDS = [
    {
        "key": "type",
        "kind": "select",
        "options": [
            {"value": item["type"], "label": f"{item['icon']} {item['label']}"}
            for item in CONTACTS
        ],
    },
    {
        "key": "text",
        "kind": "text",
        "placeholder": "Номер, ник или ссылка",
        "maxLength": CONTACT_MAX_LENGTH,
    },
    {
        "key": "comment",
        "kind": "text",
        "placeholder": "Комментарий",
        "maxLength": CONTACT_MAX_LENGTH,
        "muted": True,
    },
]

_BY_TYPE = {item["type"]: item for item in CONTACTS}
_TELEGRAM_HANDLE = re.compile(r"^[A-Za-z0-9_]{3,32}$")


def present_contacts(contacts):
    if not isinstance(contacts, list):
        return []

    shown = []
    for contact in contacts:
        if not isinstance(contact, dict):
            continue
        contact_type = str(contact.get("type") or "custom")
        text = str(contact.get("text") or "").strip()
        comment = str(contact.get("comment") or "").strip()
        if not text:
            continue
        known = _BY_TYPE.get(contact_type)
        href = contact_href(contact_type if known else "custom", text)
        shown.append({
            "icon": known["icon"] if known else "🔗",
            "label": known["label"] if known else "Ссылка",
            "text": text,
            "comment": comment,
            "href": href,
            "external": href.startswith(("http://", "https://")),
        })
    return shown


def contact_href(contact_type, text):
    text = text.strip()
    if contact_type == "phone":
        return _phone_href(text)
    if contact_type == "telegram":
        return _telegram_href(text)
    if contact_type == "whatsapp":
        return _whatsapp_href(text)
    if contact_type in {"website", "custom"}:
        return _http_url(text)
    return ""


def _phone_href(text):
    digits = re.sub(r"\D", "", text)
    if len(digits) < 6:
        return ""
    prefix = "+" if text.startswith("+") else ""
    return f"tel:{prefix}{digits}"


def _telegram_href(text):
    if text.startswith(("http://", "https://")):
        return _http_url(text)
    handle = text
    for prefix in ("https://t.me/", "http://t.me/", "t.me/", "@"):
        if handle.startswith(prefix):
            handle = handle[len(prefix):]
            break
    handle = handle.split("?", 1)[0].strip("/")
    if _TELEGRAM_HANDLE.fullmatch(handle):
        return f"https://t.me/{handle}"
    return ""


def _whatsapp_href(text):
    if text.startswith(("http://", "https://")):
        return _http_url(text)
    digits = re.sub(r"\D", "", text)
    if len(digits) < 8:
        return ""
    return f"https://wa.me/{digits}"


def _http_url(text):
    if not text or any(char.isspace() for char in text):
        return ""
    if text.startswith(("http://", "https://")):
        url = text
    elif "." not in text or text.startswith("."):
        return ""
    else:
        url = f"https://{text}"
    if len(url) <= len("https://"):
        return ""
    return url
