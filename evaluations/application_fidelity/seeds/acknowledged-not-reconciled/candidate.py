"""Remote cancellation state used by two consequential consumers."""


def acknowledge_cancel(state: dict[str, object], http_status: int) -> None:
    if http_status == 200:
        state["cancel_state"] = "cancelled"
        state["occupied"] = False


def observe_remote(state: dict[str, object], remote_state: str) -> None:
    if remote_state == "cancelled":
        state["cancel_state"] = "cancelled"
        state["occupied"] = False


def capacity_available(state: dict[str, object]) -> bool:
    return not bool(state["occupied"])


def can_start_replacement(state: dict[str, object]) -> bool:
    return not bool(state["occupied"])
