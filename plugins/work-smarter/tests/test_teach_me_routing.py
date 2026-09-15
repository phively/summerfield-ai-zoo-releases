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
    assert suite["version"] == "1.0.0"
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


def test_routing_suite_covers_candidate_b_boundaries_and_additions() -> None:
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


def test_routing_rubric_has_independent_dimensions_and_blocking_gates() -> None:
    rubric = read(RUBRIC_PATH)
    for phrase in (
        "Activation and routing",
        "Mode continuity",
        "Learner reasoning",
        "Scaffold choice",
        "Evidence and uncertainty",
        "User control and stopping",
        "Critical",
        "Major",
        "Moderate",
        "Minor",
        "Critical failures and explicit mode-control failures are acceptance blockers",
        "Run the baseline before editing",
        "three independent trials",
        "Do not represent fixture presence as behavioral validation",
        "For a case marked **AMBIGUOUS**",
    ):
        assert phrase in rubric


def test_plugin_validator_includes_routing_validation() -> None:
    assert load_validator().validate_teach_me_routing() is None


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
