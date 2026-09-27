"""Small normalizer whose current bytes postdate the retained receipt."""


def normalize(value: object) -> str:
    if value is None:
        return "UNKNOWN"
    return str(value).strip().casefold()
