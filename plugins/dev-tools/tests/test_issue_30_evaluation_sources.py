import hashlib
import json
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = PLUGIN_ROOT / "evals" / "issue-30"
FIXTURE_ROOT = PLUGIN_ROOT / "evals" / "fixtures" / "issue-30"


def test_issue_30_cases_cover_each_acceptance_example_with_process_limits() -> None:
    data = json.loads((EVAL_ROOT / "cases.json").read_text(encoding="utf-8"))
    cases = data["cases"]
    acceptance_examples = {case["acceptance_example"] for case in cases}

    assert acceptance_examples == {f"AE{number}" for number in range(1, 10)}
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        assert case["target"] in {"better-benchmarks", "code-quality-review"}
        assert case["input"]
        assert case["expected_route"]
        assert case["allowed_operations"]
        assert case["success_criteria"]
        assert case["failure_criteria"]
        assert case["prohibited_operations"]
        assert case["evidence_requirements"]

    paired = {case["paired_control"] for case in cases if case.get("paired_control")}
    assert {"bb-evidence-claim-scope", "cqr-independence-claim"} <= paired


def test_issue_30_fixture_manifest_resolves_and_hashes_tracked_sources() -> None:
    manifest = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["fixture_id"] == "issue-30-synthetic-sources"

    for source in manifest["sources"]:
        path = FIXTURE_ROOT / source["path"]
        content = path.read_bytes()
        assert f"sha256:{hashlib.sha256(content).hexdigest()}" == source["sha256"]

    case_data = json.loads((EVAL_ROOT / "cases.json").read_text(encoding="utf-8"))
    known_sources = {source["id"] for source in manifest["sources"]}
    for case in case_data["cases"]:
        assert set(case.get("fixture_refs", [])) <= known_sources


def test_issue_30_protocol_and_rubric_keep_runs_and_publication_bounded() -> None:
    protocol = (EVAL_ROOT / "protocol.md").read_text(encoding="utf-8").lower()
    rubric = (EVAL_ROOT / "rubric.md").read_text(encoding="utf-8").lower()

    for candidate in ("superb skills extension", "better-benchmarks", "coding preferences extension", "code-quality-review"):
        assert candidate in protocol
    for requirement in ("same model", "independent starting state", "raw captures", "separate approval", "general superiority"):
        assert requirement in protocol
    assert "docs/evidence" not in protocol
    for dimension in ("task usefulness", "evidence fidelity", "clarity", "boundary preservation", "routing and maintenance cost"):
        assert dimension in rubric
    for score in ("0", "1", "2"):
        assert score in rubric
    assert "unauthorized operation" in rubric
    assert "false independence" in rubric
