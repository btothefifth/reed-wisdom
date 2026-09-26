"""Keep WISDOM v1.7 delegation contracts and routes semantically complete."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compile_wisdom as compiler  # noqa: E402


SOURCE = ROOT / "WISDOM.md"
DELEGATION_RULE_IDS = ("HANDOFF-01", "LANE-01", "CAPABILITY-01")
NEW_RULE_IDS = (*DELEGATION_RULE_IDS, "ACCEPT-01")


def _rule_ids(parsed: compiler.ParsedWisdom, module_ids: tuple[str, ...]) -> set[str]:
    kernel_ids = {
        rule_id
        for section in parsed.sections
        if section.section_id in parsed.manifest["kernel_sections"]
        for rule_id in section.rule_ids
    }
    module_rule_ids = {
        rule_id
        for module_id in module_ids
        for section_id in parsed.module_by_id[module_id]["sections"]
        for rule_id in parsed.section_by_id[section_id].rule_ids
    }
    return kernel_ids | module_rule_ids


def _profile(parsed: compiler.ParsedWisdom, profile_id: str) -> dict[str, object]:
    return next(
        profile
        for profile in parsed.manifest["task_profiles"]
        if profile["id"] == profile_id
    )


def _delegation_text(parsed: compiler.ParsedWisdom) -> str:
    module = parsed.module_by_id["delegation_contract"]
    return "\n".join(
        parsed.section_by_id[section_id].body.decode("utf-8")
        for section_id in module["sections"]
    )


def _scenario_dispositions(parsed: compiler.ParsedWisdom) -> dict[str, object]:
    text = _delegation_text(parsed)
    marker = "```json\n"
    start = text.index(marker) + len(marker)
    end = text.index("\n```", start)
    parsed_value = json.loads(text[start:end])
    assert isinstance(parsed_value, dict)
    return parsed_value


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("_", " ")).casefold()


def _contains_all(text: str, terms: tuple[str, ...]) -> None:
    normalized = _normalized(text)
    for term in terms:
        assert _normalized(term) in normalized, (
            f"missing delegation contract term: {term}"
        )


def test_v17_delegation_modules_and_profiles_are_dependency_closed() -> None:
    parsed = compiler.parse_source(SOURCE)

    assert parsed.manifest["semantic_revision"] == 15
    assert [module["id"] for module in parsed.manifest["modules"]].count(
        "delegation_contract"
    ) == 1
    assert parsed.module_by_id["delegation_contract"]["sections"] == [
        "delegation_contract"
    ]
    assert parsed.module_by_id["delegation_contract"]["tags"] == ["delegation"]
    assert parsed.module_by_id["delegation_contract"]["requires"] == []

    context_module = parsed.module_by_id["context_delegation"]
    assert context_module["tags"] == ["context", "continuity"]
    assert set(context_module["requires"]) == {
        "decision_budget",
        "delegation_contract",
    }

    expected_profiles = {
        "delegated_code_change": (
            "focused",
            ("implementation", "testing", "delegation"),
            {
                "testing",
                "test_harness",
                "implementation_performance",
                "delegation_contract",
            },
        ),
        "delegated_bug_fix": (
            "focused",
            ("defect", "diagnostics", "testing", "delegation"),
            {
                "defect_diagnostics",
                "testing",
                "test_harness",
                "implementation_performance",
                "delegation_contract",
            },
        ),
        "delegated_review": (
            "focused",
            ("testing", "delegation"),
            {
                "testing",
                "test_harness",
                "implementation_performance",
                "delegation_contract",
            },
        ),
    }
    for profile_id, (mode, tags, expected_modules) in expected_profiles.items():
        profile = _profile(parsed, profile_id)
        assert profile["mode"] == mode
        assert tuple(profile["tags"]) == tags
        actual = compiler.resolve_module_ids(parsed, mode=mode, tags=tags)
        assert set(actual) == expected_modules
        assert "context_delegation" not in actual
        assert set(NEW_RULE_IDS) <= _rule_ids(parsed, actual)

    # Existing profile declarations stay stable. Effect acceptance is delivered
    # to ordinary implementation routes without loading continuity context.
    old_profiles = {
        "routine": ("fast", ()),
        "code_change": ("focused", ("implementation", "testing")),
        "bug_fix": ("focused", ("defect", "diagnostics", "testing")),
    }
    for profile_id, expected in old_profiles.items():
        profile = _profile(parsed, profile_id)
        assert (profile["mode"], tuple(profile["tags"])) == expected
        mode, tags = compiler.resolve_task_profile(parsed, profile_id)
        modules = compiler.resolve_module_ids(parsed, mode=mode, tags=tags)
        if profile_id in ("code_change", "bug_fix"):
            assert "delegation_contract" not in modules
            assert "ACCEPT-01" in _rule_ids(parsed, modules)
        else:
            assert "delegation_contract" not in modules
        assert "context_delegation" not in modules

    code_mode, code_tags = compiler.resolve_task_profile(parsed, "code_change")
    bug_mode, bug_tags = compiler.resolve_task_profile(parsed, "bug_fix")
    assert set(compiler.resolve_module_ids(parsed, mode=code_mode, tags=code_tags)) == {
        "testing",
        "test_harness",
        "implementation_performance",
    }
    assert set(compiler.resolve_module_ids(parsed, mode=bug_mode, tags=bug_tags)) == {
        "defect_diagnostics",
        "testing",
        "test_harness",
        "implementation_performance",
    }
    assert "SCOPE-01" in _rule_ids(
        parsed, compiler.resolve_module_ids(parsed, mode=code_mode, tags=code_tags)
    )
    assert "SEM-01" in _rule_ids(
        parsed, compiler.resolve_module_ids(parsed, mode=code_mode, tags=code_tags)
    )
    assert "EVIDENCE-01" in _rule_ids(
        parsed, compiler.resolve_module_ids(parsed, mode=code_mode, tags=code_tags)
    )
    for profile_id in (
        "delegated_code_change",
        "delegated_bug_fix",
        "delegated_review",
    ):
        mode, tags = compiler.resolve_task_profile(parsed, profile_id)
        routed_rules = _rule_ids(parsed, compiler.resolve_module_ids(parsed, mode=mode, tags=tags))
        assert {"SCOPE-01", "SEM-01", "IMPACT-01", "EVIDENCE-01"} <= routed_rules
    delegated_bug = _profile(parsed, "delegated_bug_fix")
    assert "REPAIR-01" in _rule_ids(
        parsed,
        compiler.resolve_module_ids(
            parsed, mode=delegated_bug["mode"], tags=delegated_bug["tags"]
        ),
    )
    assert "REPAIR-01" in _rule_ids(
        parsed, compiler.resolve_module_ids(parsed, mode=bug_mode, tags=bug_tags)
    )

    for profile_id in ("protocol_change", "external_effect_change"):
        mode, tags = compiler.resolve_task_profile(parsed, profile_id)
        assert mode == "substantial"
        assert {"context_delegation", "delegation_contract"} <= set(
            compiler.resolve_module_ids(parsed, mode=mode, tags=tags)
        )

    # The complete substantial view still carries the full delegation closure;
    # full mode remains a direct-source route for unknown impact.
    assert {"context_delegation", "delegation_contract"} <= set(
        compiler.resolve_module_ids(parsed, mode="substantial")
    )
    assert parsed.view_by_mode["full"]["source_direct"] is True
    assert compiler.resolve_module_ids(parsed, mode="full") == ()


def test_v17_delegation_rules_have_one_owner_each_and_a_typed_handoff() -> None:
    parsed = compiler.parse_source(SOURCE)
    section = parsed.section_by_id["delegation_contract"]
    delegation = _delegation_text(parsed)

    assert section.rule_ids == DELEGATION_RULE_IDS
    assert parsed.section_by_id["implementation"].rule_ids.count("ACCEPT-01") == 1
    for rule_id in DELEGATION_RULE_IDS:
        assert section.rule_ids.count(rule_id) == 1
        assert delegation.count(f"`{rule_id}`") >= 1

    _contains_all(
        delegation,
        (
            "lane_id_and_generation:",
            "objective_and_non_goals:",
            "baseline:",
            "decisions:",
            "scope:",
            "proof:",
            "result_contract:",
            "only a settled, generation-bound lane charter",
            "exact source revision and generation plus hashes",
            "baseline binds the exact bytes the lane may inspect or change",
            "delegated list, each with authority and acceptance boundary",
            "reachable boundary",
            "independent oracle",
            "charter may bound an unknown only when its irrelevance",
            "every delegated decision, action, and proof obligation",
            "materially ambiguous",
            "stale, mixed-generation, or unbounded charter",
            "rejected or escalated before mutation",
            "discovers a dependency or decision outside its declared scope",
            "stops only the affected work",
            "preserves completed evidence",
            "returns the exact boundary",
            "may not silently expand its authority",
            "lane_role:",
            "contract_state:",
            "parent_objective:",
            "objective_generation:",
            "semantic_inputs_outputs:",
            "production_path:",
            "lifecycle_and_identity:",
            "canonical_owner:",
            "required_and_preserved_behavior:",
            "unresolved_questions:",
            "forbidden_surfaces:",
            "contract_not_ready_for_implementation",
            "canonical_owner_unavailable",
            "root_reserved list and delegated list",
            "`settled` admits bounded mutation",
            "`bounded_unknowns` admits only the unknowns",
            "`research_only` admits discovery without production mutation",
        ),
    )


def test_v17_lane_roles_root_triage_and_real_production_proof_owners() -> None:
    parsed = compiler.parse_source(SOURCE)
    delegation = _normalized(_delegation_text(parsed))

    _contains_all(
        delegation,
        (
            "implementer",
            "focused reviewer",
            "root integrator",
            "feature reviewer",
            "owned delta",
            "semantic frontier",
            "advisory findings",
            "concrete counterexamples and proof gaps",
            "root integrator classifies each finding",
            "production defect",
            "test or fixture defect",
            "contract ambiguity",
            "unproved claim",
            "duplicate mechanism",
            "rejected finding",
            "reviewer output alone never changes production code, scope, or acceptance",
            "feature reviewer examines the integrated delta and cross-lane "
            "interactions",
            "earliest reachable failing boundary",
            "canonical owner",
            "impossible input through a public entrypoint",
            "test-design defect",
            "not permission to weaken production checks",
            "reachable native entrypoint",
            "canonical store reuse API path",
            "preserve both the entrypoint's real constraints and the reuse "
            "behavior's direct oracle",
            "unreachable_or_impossible_requirement",
            "valid but out of scope",
            "false positive",
            "valid but out-of-scope work is escalated for re-chartering",
        ),
    )
    assert re.search(
        r"impossible reuse demand .*? is classified as `unreachable or impossible requirement` and a test-design defect",
        delegation,
    )
    assert re.search(
        r"valid but out-of-scope work is escalated for re-chartering; a false positive is rejected",
        delegation,
    )

    # An executor entrypoint that always creates a new batch cannot prove reuse.
    # The contract must reject that impossible combined demand and preserve both
    # real proof owners.


def test_v17_capability_is_model_neutral_and_escalation_keeps_prior_evidence() -> None:
    parsed = compiler.parse_source(SOURCE)
    delegation = _normalized(_delegation_text(parsed))

    _contains_all(
        delegation,
        (
            "capability_assignment:",
            "minimum_sufficient_capabilities",
            "selected_worker_capabilities",
            "evidence_of_sufficiency",
            "cost_latency_tradeoff",
            "lowest cost and latency",
            "strongest independent reviewer",
            "minimum sufficient capabilities",
            "selected worker",
            "concrete sufficiency evidence",
            "model-neutral",
            "does not prescribe a model vendor or product name",
            "escalate or reassign",
            "evidence changes the lane's shape, scope, or risk",
            "preserve completed evidence",
            "exact source, frontier, and environment generations remain unchanged",
            "invalidate only receipts whose dependencies changed",
            "inherits the accepted generation-bound charter and evidence",
        ),
    )
    assert "sol high" not in delegation
    assert "luna high" not in delegation
    assert "sol xhigh" not in delegation


def test_v17_acceptance_cutpoint_conserves_partial_and_uncertain_effects() -> None:
    parsed = compiler.parse_source(SOURCE)
    implementation = _normalized(
        parsed.section_by_id["implementation"].body.decode("utf-8")
    )

    _contains_all(
        implementation,
        (
            "acceptance cutpoint",
            "process exception",
            "timeout",
            "nonzero exit",
            "missing result",
            "does not prove that zero work or effects were accepted",
            "preserve the current owner",
            "if acceptance crossed or state is uncertain",
            "reconcile that exact member and its effects before retry",
            "track submitted members as distinct identities",
            "conserve them across disjoint `accepted`, `rejected`, `pending`, "
            "and `unknown` sets",
            "terminal acceptance requires no unresolved member",
            "classify it `not_accepted` and release that member's ownership",
            "member a was accepted and creating member b raises",
            "retain a's ownership through its terminal result",
            "reconcile b's creation outcome before retrying the batch",
            "never convert a partial return or uncertain effect into an empty "
            "result or blanket retry",
        ),
    )
    assert re.search(
        r"independent boundary evidence proves a pristine pre-cutpoint failure .*? classify it `not accepted` and release that member's ownership",
        implementation,
    )
    assert re.search(
        r"if acceptance crossed or state is uncertain, preserve the current owner and reconcile that exact member and its effects before retry",
        implementation,
    )
    assert re.search(
        r"member a was accepted and creating member b raises, retain a's ownership through its terminal result and reconcile b's creation outcome before retrying the batch",
        implementation,
    )


def test_v17_required_scenario_dispositions_are_typed_and_exact() -> None:
    scenarios = _scenario_dispositions(compiler.parse_source(SOURCE))

    assert scenarios == {
        "unknown_api_semantics": {
            "contract_state": "research_only",
            "result": "contract_not_ready_for_implementation",
            "production_mutation": "forbidden",
        },
        "missing_canonical_owner": {
            "result": "block",
            "reason": "canonical_owner_unavailable",
            "production_mutation": "forbidden",
        },
        "settled_contract": {
            "contract_state": "settled",
            "result": "proceed_with_bounded_mutation",
            "authority": "charter_only",
        },
        "irrelevant_bounded_unknowns": {
            "contract_state": "bounded_unknowns",
            "required_evidence": "prove_irrelevance_to_each_delegated_decision_action_and_proof",
            "result": "proceed_with_bounded_mutation",
            "unknowns": "remain_explicit_and_bounded",
        },
        "stale_or_mixed_baseline": {
            "result": "reject_before_mutation",
            "prior_generation_evidence": "preserve_as_historical",
        },
        "out_of_scope_dependency": {
            "result": "stop_affected_work_and_escalate",
            "unaffected_evidence": "preserve",
        },
        "capability_reassignment": {
            "unchanged_generation_evidence": "preserve",
            "changed_dependency_receipts": "invalidate_only_these",
        },
        "capability_selection": {
            "required_record": "minimum_sufficient_capabilities_worker_capabilities_sufficiency_evidence_cost_latency_tradeoff",
            "selection": "lowest_cost_latency_worker_that_meets_proof_and_authority_need",
            "reassignment": "preserve_unaffected_evidence",
        },
        "focused_review": {
            "reviewer_result": "advisory_findings_and_proof_gaps",
            "root_integrator": "classify_each_finding_before_acceptance",
        },
        "feature_review": {
            "review_frontier": "integrated_delta_and_cross_lane_interactions",
            "root_integrator": "retains_final_classification_and_acceptance",
        },
        "fixture_design_defect": {
            "classification": "test_or_fixture_defect",
            "repair_owner": "earliest_fixture_producer",
            "production_guard": "preserve",
            "valid_downstream_assertion": "retain",
        },
        "valid_review_finding": {
            "classification": "production_defect",
            "repair_owner": "canonical_production_owner",
            "acceptance": "rerun_affected_independent_oracle_after_fix",
        },
        "cross_lane_incompatibility": {
            "detector": "feature_reviewer_integrated_delta_and_cross_lane_frontier",
            "result": "return_finding_to_root_integrator",
            "acceptance": "blocked_until_root_classification_and_reconciliation",
        },
        "impossible_reuse_through_create_only_entrypoint": {
            "classification": "unreachable_or_impossible_requirement",
            "entrypoint_proof": "prove_actual_constraints",
            "reuse_proof": "test_canonical_store_api_directly",
        },
        "pristine_pre_cutpoint_failure": {
            "required_evidence": "independent_proof_of_no_accepted_work_or_effect",
            "result": "not_accepted",
            "ownership": "release",
        },
        "post_cutpoint_or_uncertain_effect": {
            "ownership": "retain_current_owner",
            "retry": "forbidden_until_exact_member_reconciled",
        },
        "member_a_accepted_member_b_creation_raises": {
            "member_a": "retain_owner_through_terminal_result",
            "member_b": "reconcile_creation_before_batch_retry",
        },
    }


def test_v17_lifecycle_keeps_role_evidence_distinct_when_stages_collapse() -> None:
    parsed = compiler.parse_source(SOURCE)
    delegation = _normalized(_delegation_text(parsed))

    for state in (
        "prepared",
        "admitted",
        "active",
        "result_submitted",
        "root_classified",
        "accepted",
        "rejected",
        "returned_for_rework",
        "blocked",
        "cancelled",
        "failed",
        "superseded",
        "escalated",
    ):
        assert state.replace("_", " ") in delegation
    _contains_all(
        delegation,
        (
            "stages may share one durable record or be collapsed",
            "evidence for each applicable transition",
            "per-member cutpoint remains independently inspectable",
            "process termination, review completion, and requested disposition "
            "are separate facts",
            "root acceptance",
        ),
    )


def test_v17_lane_result_is_a_typed_evidence_carrier() -> None:
    parsed = compiler.parse_source(SOURCE)
    delegation = _normalized(_delegation_text(parsed))

    _contains_all(
        delegation,
        (
            "lane_result:",
            "lane_id_and_generation:",
            "source:",
            "delta:",
            "semantic_frontier:",
            "proof:",
            "review:",
            "member_outcomes:",
            "uncertainties:",
            "discovered_out_of_scope_dependencies:",
            "contract_questions:",
            "escalation_trigger:",
            "implementation_status:",
            "test_status:",
            "acceptance_cutpoint_state:",
            "requested_root_disposition:",
            "accept | reject | rework | escalate | block",
        ),
    )
