"""Reports update claimed slots; absence of a slot permits replacement."""


def record_outcome(slots: dict[str, dict[str, str]], slot_id: str, outcome: str) -> None:
    if outcome in {"timeout", "creation_failed", "completed"}:
        slots.pop(slot_id, None)
    elif outcome == "accepted" and slot_id in slots:
        slots[slot_id] = {"owner": "worker", "status": "running"}


def can_replace(slots: dict[str, dict[str, str]], slot_id: str) -> bool:
    return slot_id not in slots
