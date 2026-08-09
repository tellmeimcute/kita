from html import escape as _escape


def quote(value: str | None) -> str | None:
    if value is None:
        return None
    return _escape(value)
