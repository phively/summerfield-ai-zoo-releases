import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_issue_30_handoff_contracts_define_complete_public_boundaries() -> None:
    contract = (ROOT / "shared" / "handoff-contracts.md").read_text(encoding="utf-8")
    headings = (
        "## Caller to Code Quality Review: bounded review request",
        "## Code Quality Review to Coding Preferences: optional convention consultation",
    )
    required_fields = (
        "Trigger",
        "Required input",
        "Expected output",
        "Authority and provenance",
        "Uncertainty and failure",
    )

    for heading in headings:
        assert heading in contract
        start = contract.index(heading)
        end = contract.find("\n## ", start + len(heading))
        section = contract[start:] if end < 0 else contract[start:end]
        assert all(field in section for field in required_fields)


def test_issue_30_regressions_cover_direct_mixed_and_optional_routes() -> None:
    data = json.loads((ROOT / "evals" / "regression.json").read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in data["cases"]}
    expected_ids = {
        "benchmark-critique-direct",
        "benchmark-design-interview",
        "benchmark-instruction-evaluation-single-owner",
        "benchmark-mixed-instruction-evaluation",
        "quality-review-requested",
        "quality-review-preferences-only-when-unresolved",
        "quality-review-ordinary-coding-no-review",
        "quality-review-no-tool",
        "quality-review-preferences-unavailable",
    }

    assert expected_ids <= cases.keys()
    for case_id in expected_ids:
        case = cases[case_id]
        assert case["input"]
        assert case["intended_behavior"]
        assert case["success_criteria"]
        assert case["failure_criteria"]

    assert cases["benchmark-critique-direct"]["expected_skills"] == ["superb-skills"]
    assert cases["quality-review-requested"]["expected_skills"] == ["code-quality-review"]
    assert "code-quality-review" not in cases["quality-review-ordinary-coding-no-review"]["expected_skills"]

    mixed = cases["benchmark-mixed-instruction-evaluation"]
    assert mixed["expected_skills"] == ["superb-skills"]
    assert "single superb skills owner" in mixed["intended_behavior"].lower()


def test_issue_30_no_tool_route_preserves_the_explicit_tool_boundary() -> None:
    data = json.loads((ROOT / "evals" / "regression.json").read_text(encoding="utf-8"))
    case = next(case for case in data["cases"] if case["id"] == "quality-review-no-tool")
    requirements = " ".join(case["success_criteria"] + case["failure_criteria"]).lower()

    assert "no-tool" in case["intended_behavior"].lower()
    assert "commands" in requirements
    assert "spawning" in requirements or "spawn" in requirements
    assert "retrieval" in requirements or "retrieve" in requirements
