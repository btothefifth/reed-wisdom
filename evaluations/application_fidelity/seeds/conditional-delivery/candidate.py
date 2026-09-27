"""A small delivery gate with mode-dependent prerequisites."""


def required_sources(mode: str) -> tuple[str, ...]:
    return ("content",)


def can_deliver(mode: str, sources: dict[str, str]) -> bool:
    if mode not in {"local", "remote"}:
        return False
    return all(sources.get(name) == "ready" for name in required_sources(mode))


def deliver(mode: str, sources: dict[str, str]) -> str:
    return "delivered" if can_deliver(mode, sources) else "waiting"
