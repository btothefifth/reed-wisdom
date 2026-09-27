"""A planner with final setup and a destination selector."""


class Planner:
    def __init__(self, clock):
        self.clock = clock

    def prepare(self) -> None:
        self.clock = lambda: 0

    def timestamp(self) -> int:
        return self.clock()


def jobs(destinations: list[tuple[str, bool]]) -> list[str]:
    return [name for name, enabled in destinations if enabled]
