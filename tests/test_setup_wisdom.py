from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import setup_wisdom as setup  # noqa: E402


@pytest.fixture
def installation(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "bundle" / "WISDOM.md"
    source.parent.mkdir()
    source.write_text("# WISDOM\n", encoding="utf-8")
    home = tmp_path / "codex-home"
    home.mkdir()
    return source, home


def run(source: Path, home: Path, *, answers=(), schema=None, catalog=None, interactive=True):
    messages: list[str] = []
    choices = iter(answers)
    setup.run_setup(
        source, home, schema_path=schema, catalog_path=catalog,
        interactive=interactive, input_func=lambda _: next(choices),
        output=messages.append, probe_cli=False,
    )
    return "\n".join(messages)


def test_noninteractive_and_decline_leave_everything_unchanged(installation):
    source, home = installation
    agents = home / "AGENTS.md"
    config = home / "config.toml"
    workflow = home / "workflows" / "keep.md"
    workflow.parent.mkdir()
    workflow.write_bytes(b"untouched")
    agents.write_bytes(b"Existing instruction.\r\n")
    config.write_bytes(b"model_context_window = 500000\n")
    before = (agents.read_bytes(), config.read_bytes(), workflow.read_bytes())
    result = run(source, home, interactive=False)
    assert "AGENTS exact delta" in result
    assert (agents.read_bytes(), config.read_bytes(), workflow.read_bytes()) == before
    assert not list(home.glob("*.bak"))
    result = run(source, home, answers=["no"])
    assert "AGENTS guidance skipped" in result
    assert (agents.read_bytes(), config.read_bytes(), workflow.read_bytes()) == before


def test_effective_override_wins_and_rerun_is_idempotent(installation):
    source, home = installation
    base = home / "AGENTS.md"
    override = home / "AGENTS.override.md"
    base.write_bytes(b"Base stays.\n")
    override.write_bytes(b"Effective override.\n")
    result = run(source, home, answers=["YES"])
    assert f"Effective global instruction target: {override}" in result
    assert base.read_bytes() == b"Base stays.\n"
    assert source.resolve().as_posix().encode() in override.read_bytes()
    assert b"For each task, load a verified view" in override.read_bytes()
    assert b"Explicit current instructions and verified facts take precedence" in override.read_bytes()
    assert len(list(home.glob("AGENTS.override.md.before-wisdom-*.bak"))) == 1
    prior = override.read_bytes()
    result = run(source, home)
    assert "equivalent source-specific" in result
    assert override.read_bytes() == prior
    assert len(list(home.glob("AGENTS.override.md.before-wisdom-*.bak"))) == 1


def test_existing_equivalent_guidance_skips_duplicate(installation):
    source, home = installation
    agents = home / "AGENTS.md"
    agents.write_text(f"Read and follow `{source.resolve().as_posix()}` for engineering work.\n", encoding="utf-8")
    before = agents.read_bytes()
    result = run(source, home)
    assert "equivalent source-specific" in result
    assert agents.read_bytes() == before


def test_conflicting_wisdom_source_refuses_unsafe_append(installation):
    source, home = installation
    agents = home / "AGENTS.md"
    original = b"Read and follow `C:/old/WISDOM.md` for all tasks.\n"
    agents.write_bytes(original)
    with pytest.raises(setup.SetupError, match="different WISDOM guidance"):
        run(source, home, answers=["YES"])
    assert agents.read_bytes() == original


def test_obsolete_path_mention_does_not_skip_new_guidance(installation):
    source, home = installation
    agents = home / "AGENTS.md"
    old = f"The former guide at {source.resolve().as_posix()} is obsolete. Read README.md instead.\n".encode()
    agents.write_bytes(old)
    result = run(source, home, answers=["YES"])
    assert "AGENTS exact delta" in result
    assert agents.read_bytes().startswith(old)
    assert b"For each task, load a verified view" in agents.read_bytes()


def test_migration_read_mention_is_not_equivalent_guidance(installation):
    source, home = installation
    agents = home / "AGENTS.md"
    old = f"Migration note: Read `{source.resolve().as_posix()}` for historical context.\n".encode()
    agents.write_bytes(old)
    result = run(source, home, answers=["YES"])
    assert "AGENTS exact delta" in result
    assert agents.read_bytes().startswith(old)
    assert b"For each task, load a verified view" in agents.read_bytes()


def test_empty_override_does_not_shadow_nonempty_base(installation):
    source, home = installation
    (home / "AGENTS.override.md").write_bytes(b"\n")
    (home / "AGENTS.md").write_bytes(b"Base.\n")
    run(source, home, answers=["YES"])
    assert (home / "AGENTS.override.md").read_bytes() == b"\n"
    assert source.resolve().as_posix().encode() in (home / "AGENTS.md").read_bytes()


def test_model_conflict_per_key_consent_preserves_toml_and_comment(installation):
    source, home = installation
    config = home / "config.toml"
    original = b"# owner comment\nmodel = 'test-model'\nmodel_context_window = 500000\nmodel_auto_compact_token_limit = 232560\n[features]\ncode_mode = { enabled = true }\n"
    config.write_bytes(original)
    catalog = home / "models.json"
    catalog.write_text(json.dumps({"models": [{"slug": "test-model", "context_window": 272000}]}), encoding="utf-8")
    result = run(source, home, answers=["no", "YES"], catalog=catalog)
    assert "conflicts with selected model's catalog window (272000)" in result
    assert "model_context_window = 500000" not in config.read_text()
    assert b"model_auto_compact_token_limit = 232560" in config.read_bytes()
    assert b"# owner comment" in config.read_bytes()
    assert len(list(home.glob("config.toml.before-wisdom-*.bak"))) == 1
    assert list(home.glob("config.toml.before-wisdom-*.bak"))[0].read_bytes() == original


def test_unsupported_schema_key_requires_its_own_consent(installation):
    source, home = installation
    config = home / "config.toml"
    config.write_bytes(b"[agents]\nenabled = true\nmax_concurrent_threads_per_session = 6\n")
    schema = home / "schema.json"
    schema.write_text(json.dumps({
        "properties": {"agents": {"properties": {"enabled": {"type": "boolean"}}, "additionalProperties": False}},
        "additionalProperties": False,
    }), encoding="utf-8")
    result = run(source, home, answers=["no", "YES"], schema=schema)
    assert "agents.max_concurrent_threads_per_session: unsupported" in result
    assert b"enabled = true" in config.read_bytes()
    assert b"max_concurrent_threads_per_session" not in config.read_bytes()


def test_schema_property_presence_does_not_validate_wrong_value_type(installation):
    source, home = installation
    config = home / "config.toml"
    config.write_bytes(b"model_context_window = 500000\n")
    schema = home / "schema.json"
    schema.write_text(json.dumps({
        "properties": {"model_context_window": {"type": "string"}},
        "additionalProperties": False,
    }), encoding="utf-8")
    result = run(source, home, answers=["no", "no"], schema=schema)
    assert "model_context_window: conflicts with supplied schema value constraints" in result
    assert "valid against supplied schema" not in result
    assert config.read_bytes() == b"model_context_window = 500000\n"


def test_terminal_anyof_boolean_is_not_misread_as_object_only(installation):
    source, home = installation
    config = home / "config.toml"
    config.write_bytes(b"[features]\ncontext_management = true\n")
    schema = home / "schema.json"
    schema.write_text(json.dumps({
        "properties": {"features": {"properties": {"context_management": {
            "anyOf": [{"type": "boolean"}, {"type": "object", "properties": {"experimental_mode": {"type": "boolean"}}}]
        }}}}
    }), encoding="utf-8")
    result = run(source, home, answers=["no"], schema=schema)
    assert "features.context_management: schema-presence-only" in result
    assert "Config exact delta" not in result
    assert config.read_bytes() == b"[features]\ncontext_management = true\n"


def test_unsupported_schema_constraint_does_not_claim_valid(installation):
    source, home = installation
    config = home / "config.toml"
    config.write_bytes(b"model_context_window = 5\n")
    schema = home / "schema.json"
    schema.write_text(json.dumps({
        "properties": {"model_context_window": {"type": "integer", "multipleOf": 2}}
    }), encoding="utf-8")
    result = run(source, home, answers=["no"], schema=schema)
    assert "model_context_window: schema-presence-only" in result
    assert "valid against supplied schema" not in result
    assert "Config exact delta" not in result


def test_unresolvable_schema_ref_is_advisory_only(installation):
    source, home = installation
    config = home / "config.toml"
    config.write_bytes(b"model_context_window = 500000\n")
    schema = home / "schema.json"
    schema.write_text(json.dumps({
        "properties": {"model_context_window": {"$ref": "#/$defs/missing"}},
        "$defs": {"missing": True},
    }), encoding="utf-8")
    result = run(source, home, answers=["no"], schema=schema)
    assert "schema-presence-only" in result
    assert "Config exact delta" not in result


def test_unsafe_config_merge_and_invalid_toml_refuse(installation):
    source, home = installation
    config = home / "config.toml"
    config.write_bytes(b"model = 'test-model'\nmodel_context_window = 500000 # keep this note\n")
    catalog = home / "models.json"
    catalog.write_text(json.dumps({"models": [{"slug": "test-model", "context_window": 272000}]}), encoding="utf-8")
    result = run(source, home, answers=["no"], catalog=catalog)
    assert "manual review required" in result
    assert config.read_bytes().endswith(b"# keep this note\n")
    config.write_bytes(b"this is not toml\n")
    with pytest.raises(setup.SetupError, match="cannot be parsed"):
        run(source, home, answers=["no"], catalog=catalog)


def test_no_access_to_workflow_tree_even_when_present(installation, monkeypatch):
    source, home = installation
    workflow = home / "workflows" / "personal.md"
    workflow.parent.mkdir()
    workflow.write_bytes(b"private")
    original_read = Path.read_bytes

    def guarded_read(path):
        if "workflow" in str(path).casefold():
            raise AssertionError("installer accessed workflow data")
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    run(source, home, answers=["no"])
    assert original_read(workflow) == b"private"


def test_invalid_explicit_evidence_and_instruction_budget_prevent_writes(installation):
    source, home = installation
    config = home / "config.toml"
    config.write_bytes(b"project_doc_max_bytes = 64\n")
    agents = home / "AGENTS.md"
    agents.write_bytes(b"Existing.\n")
    bad_schema = home / "schema.json"
    bad_schema.write_bytes(b"not json")
    with pytest.raises(setup.SetupError, match="explicit JSON evidence file is invalid"):
        run(source, home, answers=["YES"], schema=bad_schema)
    assert agents.read_bytes() == b"Existing.\n"
    result = run(source, home, answers=["YES"])
    assert "exceeds this config's instruction byte limit" in result
    assert agents.read_bytes() == b"Existing.\n"
    assert not list(home.glob("*.bak"))


def test_every_config_removal_needs_separate_yes(installation):
    source, home = installation
    config = home / "config.toml"
    config.write_bytes(b"model = 'test-model'\nmodel_context_window = 500000\nmodel_auto_compact_token_limit = 300000\n")
    catalog = home / "models.json"
    catalog.write_text(json.dumps({"models": [{"slug": "test-model", "context_window": 272000}]}), encoding="utf-8")
    result = run(source, home, answers=["no", "YES", "no"], catalog=catalog)
    assert result.count("Config exact delta") == 2
    assert b"model_context_window" not in config.read_bytes()
    assert b"model_auto_compact_token_limit = 300000" in config.read_bytes()
    assert len(list(home.glob("config.toml.before-wisdom-*.bak"))) == 1


@pytest.mark.parametrize("prefix", ["profile = 'large'\n", "model_provider = 'custom'\n"])
def test_profile_or_custom_provider_does_not_infer_catalog_limit(installation, prefix):
    source, home = installation
    config = home / "config.toml"
    original = (prefix + "model = 'test-model'\nmodel_context_window = 500000\n").encode()
    config.write_bytes(original)
    catalog = home / "models.json"
    catalog.write_text(json.dumps({"models": [{"slug": "test-model", "context_window": 272000}]}), encoding="utf-8")
    result = run(source, home, answers=["no"], catalog=catalog)
    assert "Config exact delta" not in result
    assert config.read_bytes() == original


def test_noninteractive_missing_home_creates_no_files(installation):
    source, home = installation
    missing = home / "fresh"
    run(source, missing, interactive=False)
    assert not missing.exists()


def test_config_change_after_diagnostics_refuses_stale_remediation(installation):
    source, home = installation
    config = home / "config.toml"
    config.write_bytes(b"model = 'test-model'\nmodel_context_window = 500000\n")
    catalog = home / "models.json"
    catalog.write_text(json.dumps({"models": [{"slug": "test-model", "context_window": 272000}]}), encoding="utf-8")

    def change_during_agents_prompt(_):
        config.write_bytes(b"model = 'different-model'\nmodel_context_window = 500000\n")
        return "no"

    with pytest.raises(setup.SetupError, match="changed after diagnostics"):
        setup.run_setup(source, home, catalog_path=catalog, interactive=True,
                        input_func=change_during_agents_prompt, output=lambda _: None, probe_cli=False)
    assert b"model = 'different-model'" in config.read_bytes()
    assert not list(home.glob("*.bak"))


def test_edit_after_initial_check_is_not_overwritten(installation, monkeypatch):
    source, home = installation
    agents = home / "AGENTS.md"
    agents.write_bytes(b"Original.\n")
    original_atomic = setup._atomic_bytes

    def concurrent_change(path, raw, *, mode, expected_target=setup._UNSET):
        if path == agents and expected_target is not setup._UNSET:
            agents.write_bytes(b"Concurrent owner edit.\n")
        return original_atomic(path, raw, mode=mode, expected_target=expected_target)

    monkeypatch.setattr(setup, "_atomic_bytes", concurrent_change)
    with pytest.raises(setup.SetupError, match="changed during write"):
        run(source, home, answers=["YES"])
    assert agents.read_bytes() == b"Concurrent owner edit.\n"
    assert not (home / ".setup-wisdom.lock").exists()
