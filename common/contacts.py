import re

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

CONTACT_BY_TYPE = {item["type"]: item for item in CONTACTS}
TELEGRAM_HANDLE = re.compile(r"^[A-Za-z0-9_]{3,32}$")


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
        known = CONTACT_BY_TYPE.get(contact_type)
        href = ""
        if contact_type == "phone":
            digits = re.sub(r"\D", "", text)
            if len(digits) >= 6:
                prefix = "+" if text.startswith("+") else ""
                href = f"tel:{prefix}{digits}"
        elif contact_type == "telegram":
            if text.startswith(("http://", "https://")):
                href = http_url(text)
            else:
                handle = text
                for prefix in ("t.me/", "@"):
                    if handle.startswith(prefix):
                        handle = handle[len(prefix):]
                        break
                handle = handle.split("?", 1)[0].strip("/")
                if TELEGRAM_HANDLE.fullmatch(handle):
                    href = f"https://t.me/{handle}"
        elif contact_type == "whatsapp":
            if text.startswith(("http://", "https://")):
                href = http_url(text)
            else:
                digits = re.sub(r"\D", "", text)
                if len(digits) >= 8:
                    href = f"https://wa.me/{digits}"
        else:
            href = http_url(text)

        shown.append({
            "icon": known["icon"] if known else "🔗",
            "label": known["label"] if known else "Ссылка",
            "text": text,
            "comment": comment,
            "href": href,
            "external": href.startswith(("http://", "https://")),
        })
    return shown


def http_url(text):
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
