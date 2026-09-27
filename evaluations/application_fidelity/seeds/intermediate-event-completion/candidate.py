"""Job state derived from worker lifecycle events."""


def run_job(terminal_result: str) -> dict[str, object]:
    state = {"started": False, "completed": False, "result": None}
    state["started"] = True
    state["completed"] = True
    state["result"] = terminal_result
    return state
