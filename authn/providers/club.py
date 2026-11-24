from datetime import datetime

from authlib.integrations.django_client import OAuth
from django.conf import settings

oauth = OAuth()
oauth.register(**settings.CLUB_OPENID_CONFIG)

PROFILE_FIELDS = ("full_name", "city", "country", "contact")


def apply_club_profile(user, data, *, fill_bio=False):
    for field in PROFILE_FIELDS:
        value = (data.get(field) or "").strip()
        if value:
            setattr(user, field, value)

    if fill_bio:
        position = (data.get("position") or "").strip()
        company = (data.get("company") or "").strip()
        headline = " — ".join(part for part in (position, company) if part)
        if headline:
            headline = f"💼 {headline}"
        bio = (data.get("bio") or "").strip()
        user.bio = "\n\n".join(part for part in (headline, bio) if part) or None

    user.club_slug = data["slug"]

    for raw, attr in (
        (data.get("membership_started_at"), "membership_started_at"),
        (data.get("membership_expires_at"), "membership_expires_at"),
    ):
        if not raw:
            continue
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        setattr(user, attr, parsed)

    hat = data.get("hat")
    if hat:
        user.hat = hat

    return user
