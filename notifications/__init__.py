def __getattr__(name):
    if name == "item_created":
        from notifications.telegram.items import item_created
        return item_created
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
