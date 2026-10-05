"""Keep runtime/context clarifications routed and the fast kernel unchanged."""
from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import compile_wisdom as compiler


def test_v113_keeps_kernel_and_route_topology_unchanged():
    parsed = compiler.parse_source(ROOT / 'WISDOM.md')
    assert parsed.manifest['semantic_revision'] == 21
    assert len(parsed.manifest['modules']) == 26
    assert len(parsed.manifest['allowed_tags']) == 40
    # The v1.12 compiled kernel is an independent retained release baseline.
    assert hashlib.sha256(parsed.kernel[len(parsed.preamble):]).hexdigest() == (
        '22179848023a8a539524d7a97df795ef9d8a79f6517c78cb62fdcc83e6448528'
    )
    assert compiler.resolve_module_ids(parsed, mode='fast', tags=[]) == ()
    assert compiler.resolve_module_ids(parsed, mode='fast', tags=['runtime_identity']) == (
        'architecture_authority', 'runtime_identity',
    )
    assert compiler.resolve_module_ids(parsed, mode='focused', tags=[]) == (
        'testing', 'test_harness', 'implementation_performance',
    )


def test_v113_clarifications_have_one_existing_module_owner():
    parsed = compiler.parse_source(ROOT / 'WISDOM.md')
    owners = {
        b'Bind identity and absence observations': 'runtime_identity',
        b'Before costly child work can endanger': 'runtime_identity',
        b'When a test carrier, fixture composition': 'test_harness',
        b'Run ordinary pure, mocked, and local temporary-store tests': 'test_harness',
        b'For example, create-new private publication': 'runtime_identity',
    }
    for marker, owner in owners.items():
        assert marker not in parsed.kernel
        assert [section.section_id for section in parsed.sections if marker in section.body] == [owner]
