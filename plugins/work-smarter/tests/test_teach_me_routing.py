#!/usr/bin/env python3
"""Structural and rubric checks for the bundled teach-me routing suite."""

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUITE_PATH = ROOT / "evals" / "teach-me-routing.json"
RUBRIC_PATH = ROOT / "evals" / "teach-me-routing-scoring.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_validator():
    path = ROOT / "scripts" / "validate_plugin.py"
    spec = importlib.util.spec_from_file_location("validate_plugin", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_suite() -> dict:
    return json.loads(read(SUITE_PATH))


def test_routing_suite_has_explicit_context_protocol() -> None:
    suite = load_suite()
    assert suite["suite"] == "teach-me-routing"
    assert suite["version"] == "1.1.0"
    protocol = suite["fixture_protocol"]
    assert set(protocol) == {"context", "turns", "expected_mode_by_turn"}
    assert set(protocol["context"]) == {
        "project_instructions",
        "assistant_history",
        "tool_availability",
        "conversation_state",
    }

    cases = suite["cases"]
    assert len(cases) >= 30
    assert len({case["id"] for case in cases}) == len(cases)
    assert sum(len(case["turns"]) > 1 for case in cases) >= 12
    for case in cases:
        assert case["input"] == "\n\n".join(case["turns"])
        assert isinstance(case["context"], dict)
        assert set(case["context"]) == {
            "project_instructions",
            "assistant_history",
            "tool_availability",
            "conversation_state",
        }
        assert len(case["expected_mode_by_turn"]) == len(case["turns"])
        assert set(case["expected_mode_by_turn"]) <= {"DIRECT", "LEARNING", "AMBIGUOUS"}
        assert isinstance(case["expected_skills"], list)
        assert case["intended_behavior"]
        assert case["success_criteria"]
        assert case["failure_criteria"]


def test_routing_suite_covers_interaction_modes_and_research_routes() -> None:
    suite = load_suite()
    ids = {case["id"] for case in suite["cases"]}
    required = {
        "route-direct-factual-standalone",
        "route-direct-explanation-standalone",
        "route-explicit-understanding",
        "route-explicit-exploration",
        "route-explicit-invocation-question-form",
        "route-explicit-direct-override",
        "route-active-lesson-ordinary-question",
        "route-active-kahneman-alternate-formulations",
        "route-active-local-explanation",
        "route-active-temporary-override",
        "route-active-permanent-exit",
        "route-active-source-request-continues",
        "route-active-source-request-concludes",
        "route-review-skill-negative",
        "route-ai-analysis-direct",
        "route-ai-exploration",
        "route-ai-active-hypothesis",
        "route-direct-deliverable",
        "route-learning-practice",
        "route-ambiguous-standalone",
        "route-ambiguous-active-lesson",
        "route-project-learning-default",
        "route-research-handoff-preserves-mode",
        "route-learning-plan-deliverable",
        "route-missing-reference-fallback",
        "route-ambiguous-mode-question",
        "route-active-missing-referent",
        "route-active-supporting-task-no-continuation",
        "route-active-unrelated-task",
        "route-active-return-after-unrelated",
        "route-direct-continuing-override",
        "route-explicit-direct-subscope-learning",
        "route-kahneman-critic-hypothesis",
    }
    assert required <= ids
    assert set(suite["provenance"]) >= {"historical", "adapted", "synthetic"}
    assert {
        "route-active-kahneman-alternate-formulations",
        "route-active-source-request-concludes",
        "route-ai-analysis-direct",
        "route-ai-exploration",
        "route-ai-active-hypothesis",
        "route-direct-deliverable",
        "route-learning-practice",
        "route-kahneman-critic-hypothesis",
    } <= {
        case["id"] for case in suite["cases"] if case.get("provenance") == "adapted"
    }


def test_routing_fixture_makes_mode_transitions_observable() -> None:
    cases = {case["id"]: case for case in load_suite()["cases"]}
    assert cases["route-active-permanent-exit"]["expected_mode_by_turn"] == [
        "LEARNING",
        "DIRECT",
    ]
    assert cases["route-active-source-request-concludes"]["expected_mode_by_turn"] == [
        "LEARNING",
        "DIRECT",
    ]
    assert cases["route-active-return-after-unrelated"]["expected_mode_by_turn"] == [
        "LEARNING",
        "DIRECT",
        "LEARNING",
    ]
    assert cases["route-ambiguous-mode-question"]["expected_mode_by_turn"] == [
        "AMBIGUOUS"
    ]
    assert cases["route-project-learning-default"]["context"]["project_instructions"]


def test_bundled_teach_me_contains_the_mode_gate() -> None:
    root = ROOT / "skills" / "teach-me"
    skill = read(root / "SKILL.md")
    workflow = read(root / "references" / "teaching-workflow.md")
    personality = read(root / "references" / "personalities" / "nicer-socrates.md")
    assert "continuation of an established teaching interaction" in skill
    assert "request that merely reviews or edits this skill" in skill
    assert "chooses the interaction mode before selecting a teaching move" in skill
    for phrase in (
        "Choose the interaction mode before selecting a teaching move",
        "Honor an explicit current user instruction",
        "Once **LEARNING** mode is established",
        "A content question does not by itself end the lesson",
        "apply a relevant project learning default",
        "ask one concise mode question",
        "A direct override applies only for the turn or scope stated",
        "A learning-plan request is a deliverable",
    ):
        assert phrase in workflow
    assert "Leave interaction-mode decisions to `teaching-workflow.md`" in personality
    assert "does not end **LEARNING** mode" in personality


def test_routing_rubric_scopes_current_research_acceptance() -> None:
    rubric = read(RUBRIC_PATH)
    for heading in ("## Cases", "## Scoring", "## Execution", "## Acceptance"):
        assert heading in rubric
    for stale in ("Candidate B", "Historical interaction-mode", "Run the baseline before editing"):
        assert stale not in rubric
    cases = {case["id"] for case in load_suite()["cases"]}
    referenced = {line.split("`", 2)[1] for line in rubric.splitlines() if line.startswith("- `route-")}
    assert referenced <= cases
    assert len(referenced) == 7
    assert "Do not represent fixture presence as behavioral validation" in rubric


def test_plugin_validator_includes_routing_validation() -> None:
    assert load_validator().validate_teach_me_routing() is None


def test_research_prompt_routing_is_caller_owned() -> None:
    skill = read(ROOT / "skills" / "teach-me" / "SKILL.md")
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")
    teaching_contract = contract.split("## Teach Me to Research Briefing\n", 1)[1].split("\n## ", 1)[0]
    other_contract = contract.split("## Superb Skills to Research Briefing\n", 1)[1].split("\n## ", 1)[0]
    plan = read(ROOT / "skills" / "teach-me" / "references" / "learning-plan-research.md")
    assert "invoke `research-briefing` through the canonical contract" in skill
    assert "this contract supplies no receiver-specific exception" in teaching_contract
    assert "actual authorization and its scope" in teaching_contract
    assert "| User confirmation | Required." in other_contract
    assert "teach-me" not in research
    assert "bounded automatic-research exception" not in research
    assert "Also omit the checkpoint when the current request explicitly waives it" in research
    assert "tailored research prompt" in teaching_contract
    assert "When external research is needed" in plan
    assert "use the parent skill's research route" in plan.lower()
    assert "do not execute research when the user requested preparation only" in plan
    cases = {case["id"]: case for case in load_suite()["cases"]}
    for case_id in (
        "route-plan-research-prompt",
        "route-plan-research-checkpoint",
        "route-plan-prompt-only",
        "route-research-direct-checkpoint",
        "route-research-caller-label-negative",
        "route-plan-supplied-material",
    ):
        assert case_id in cases
    assert "research-briefing" in cases["route-plan-research-prompt"]["expected_skills"]
    assert "skip research-scope confirmation" in cases["route-plan-research-prompt"]["input"].lower()
    assert "skip research-scope confirmation" not in cases["route-plan-research-checkpoint"]["input"].lower()
    assert "research-briefing" not in cases["route-plan-prompt-only"]["expected_skills"]
    assert "research-briefing" not in cases["route-plan-supplied-material"]["expected_skills"]


def test_entire_bundled_plugin_validator_passes() -> None:
    assert load_validator().main() == 0


if __name__ == "__main__":
    tests = sorted(
        (name, value)
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    )
    for name, test in tests:
        test()
        print(f"PASS {name}")
    print(f"PASS {len(tests)} teach-me routing tests")
