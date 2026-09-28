from datetime import datetime

from authlib.integrations.django_client import OAuth
from django.conf import settings

oauth = OAuth()
oauth.register(**settings.CLUB_OPENID_CONFIG)

PROFILE_FIELDS = ("full_name", "avatar", "bio", "company", "position", "city", "country", "contact")


def apply_club_profile(user, profile):
    """Copy whatever the Club API sent. Every field is optional."""
    data = profile.get("user") if isinstance(profile, dict) else None
    if not isinstance(data, dict):
        data = {}

    for field in PROFILE_FIELDS:
        value = data.get(field)
        if isinstance(value, dict):
            value = value.get("name") or value.get("title") or ""
        if value is None:
            continue
        value = str(value).strip()
        if value:
            setattr(user, field, value)

    upvotes = data.get("upvotes")
    if isinstance(upvotes, bool) or upvotes is None:
        upvotes = None
    elif isinstance(upvotes, int):
        pass
    elif isinstance(upvotes, str) and upvotes.strip().lstrip("-").isdigit():
        upvotes = int(upvotes)
    else:
        upvotes = None
    if upvotes is not None:
        user.upvotes = upvotes

    for raw, attr in (
        (data.get("membership_started_at"), "membership_started_at"),
        (data.get("membership_expires_at"), "membership_expires_at"),
    ):
        if not raw or not isinstance(raw, str):
            continue
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        setattr(user, attr, parsed)

    hat = data.get("hat")
    if isinstance(hat, (dict, list)) and hat:
        user.hat = hat

    user.profile_cache = profile if isinstance(profile, dict) else {}
    return user
