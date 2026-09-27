"""Minimal resource-claim and child-creation lifecycle."""


def launch(registry: dict[str, str], claim_id: str, *, serialize_ok: bool, creation: str) -> str:
    registry[claim_id] = "claimant"
    if not serialize_ok:
        return "serialization_failed"
    if creation == "failed":
        return "creation_failed"
    if creation == "uncertain":
        registry.pop(claim_id, None)
        return "creation_uncertain"
    registry[claim_id] = "child"
    return "created"
