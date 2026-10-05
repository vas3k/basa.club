"""Flags a user may set on their own metadata. Add new names here."""

ALLOWED_USER_FLAGS = frozenset({
    "is_welcome_read",
})


def has_user_flag(user, name):
    if not getattr(user, "is_authenticated", False):
        return False
    return bool((user.metadata or {}).get(name))


def set_user_flag(user, name, value):
    metadata = dict(user.metadata or {})
    if metadata.get(name) is value:
        return
    metadata[name] = value
    user.metadata = metadata
    user.save(update_fields=["metadata"])
