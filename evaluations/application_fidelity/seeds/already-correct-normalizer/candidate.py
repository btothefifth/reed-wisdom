"""Normalize supported names."""


def normalize(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().casefold()
