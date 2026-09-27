"""Expiry guard followed by a serializer with an observable reach counter."""

serialize_calls = 0


def encode(record: dict[str, object], now: int) -> str:
    global serialize_calls
    if int(record["expires_at"]) <= now:
        raise ValueError("expired")
    serialize_calls += 1
    return f"{record['id']}:{record['value']}"
