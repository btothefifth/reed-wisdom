"""Check lesson delivery and preserved topology, not model application quality."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import compile_wisdom as compiler  # noqa: E402


@pytest.mark.parametrize("marker", (
    b"Use the model to choose and challenge operations",
    b"Sorted batches are not a globally sorted stream",
    b"Budget the largest intermediate state as well as the final result",
    b"For collection, begin with the supported consumers' explicit observation needs",
    b"Validate and persist admitted observations before publishing",
    b"Design sustainable retention before sustained unattended accumulation",
    b"Account for the whole physical footprint without double-counting",
    b"Keep schema guides and data reports truthful to one declared source/runtime",
))
def test_large_data_lessons_have_one_existing_owner_and_route(marker):
    parsed = compiler.parse_source(ROOT / "WISDOM.md")
    assert marker not in parsed.kernel
    assert [section.section_id for section in parsed.sections if marker in section.body] == ["storage_design"]
    selected = compiler.resolve_module_ids(parsed, mode="focused", tags=["storage"])
    assert "storage_design" in selected
    assert parsed.section_by_id["storage_design"].rule_ids == ("DATA-01",)


def test_initial_route_teaches_data_mechanisms_without_new_topology():
    parsed = compiler.parse_source(ROOT / "WISDOM.md")
    assert b"automatically\nadd the discovered `storage` route" in parsed.kernel
    assert b'when the request never says "database" or "big data"' in parsed.kernel
    assert b"already bounded unchanged path needs no new data platform" in parsed.kernel
    assert parsed.manifest["semantic_revision"] == 21
    assert len(parsed.manifest["modules"]) == 26
    assert len(parsed.manifest["allowed_tags"]) == 40
    assert compiler.resolve_module_ids(parsed, mode="fast", tags=[]) == ()
    assert len(parsed.kernel) < parsed.manifest["kernel_max_bytes"]
