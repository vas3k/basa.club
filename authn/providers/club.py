from datetime import datetime

from authlib.integrations.django_client import OAuth
from django.conf import settings

oauth = OAuth()
oauth.register(**settings.CLUB_OPENID_CONFIG)

PROFILE_FIELDS = ("full_name", "avatar", "city", "country", "contact")


def _text(value):
    if isinstance(value, dict):
        value = value.get("name") or value.get("title") or ""
    if value is None:
        return ""
    return str(value).strip()


def club_bio(profile):
    """position, company, then the club bio, joined into one markdown field."""
    data = profile.get("user") if isinstance(profile, dict) else None
    if not isinstance(data, dict):
        data = {}
    headline = " — ".join(part for part in (_text(data.get("position")), _text(data.get("company"))) if part)
    if headline:
        headline = f"💼 {headline}"
    bio = _text(data.get("bio"))
    return "\n\n".join(part for part in (headline, bio) if part)


def apply_club_profile(user, profile, *, club_slug=None, fill_bio=False):
    """Copy whatever the Club API sent. Every field is optional."""
    data = profile.get("user") if isinstance(profile, dict) else None
    if not isinstance(data, dict):
        data = {}

    for field in PROFILE_FIELDS:
        value = _text(data.get(field))
        if value:
            setattr(user, field, value)

    if fill_bio:
        user.bio = club_bio(profile) or None

    slug = _text(club_slug) or _text(data.get("slug"))
    if slug:
        user.club_slug = slug[:64]

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

    return user
