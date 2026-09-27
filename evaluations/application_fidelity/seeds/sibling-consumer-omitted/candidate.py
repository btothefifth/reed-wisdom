"""Two consumers of one lifecycle state."""


def primary_can_act(status: str) -> bool:
    return status == "ready"


def sibling_can_export(status: str) -> bool:
    return status != "blocked"
