#!/usr/bin/env python3
"""Structural and behavioral regression tests for the career-coach plugin."""

import json
import importlib.util
import re
import shutil
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = PLUGIN_ROOT / "skills"
SHARED_HANDOFF = PLUGIN_ROOT / "shared" / "handoff-contracts.md"
RECORD_MANAGEMENT = PLUGIN_ROOT / "shared" / "career-direction-records.md"
OPPORTUNITY_MANAGEMENT = PLUGIN_ROOT / "shared" / "opportunity-records.md"
RECORD_AUDITS = PLUGIN_ROOT / "shared" / "record-audits.md"
AUDIT_SCRIPT = PLUGIN_ROOT / "scripts" / "validate_record_audit.py"
SKILL_NAMES = ("career-direction", "evaluate-opportunity", "update-resume")
SHARED_LINK = "../../shared/handoff-contracts.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def skill_text(name: str) -> str:
    return read(SKILLS_ROOT / name / "SKILL.md")


def test_canonical_plugin_and_skill_structure() -> None:
    manifest = json.loads(read(PLUGIN_ROOT / ".codex-plugin" / "plugin.json"))
    assert manifest["name"] == PLUGIN_ROOT.name == "career-coach"
    assert manifest["version"] == "1.6.0"
    assert manifest["skills"] == "./skills/"
    for name in SKILL_NAMES:
        root = SKILLS_ROOT / name
        assert (root / "SKILL.md").is_file()
        assert (root / "agents" / "openai.yaml").is_file()


def test_all_skill_local_markdown_links_resolve() -> None:
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for name in SKILL_NAMES:
        skill_path = SKILLS_ROOT / name / "SKILL.md"
        for link in link_pattern.findall(read(skill_path)):
            if "://" not in link and not link.startswith("#"):
                assert (skill_path.parent / link).resolve().is_file(), (
                    f"Broken local resource link in {name}: {link}"
                )


def test_every_skill_checks_shared_context_sources() -> None:
    for name in SKILL_NAMES:
        skill = skill_text(name)
        assert "`career_direction_record.md` or a clearly equivalent" in skill
        assert "`career_direction_history.md` or its resolved" in skill
        assert "`opportunities-current.md` or a clearly equivalent" in skill
        assert "`opportunities-history.md`" in skill
        assert "`career-coach-preferences.md` or a clearly equivalent" in skill
        assert f"]({SHARED_LINK})" in skill
        assert "](../../shared/career-direction-records.md)" in skill
        assert "](../../shared/opportunity-records.md)" in skill
        assert "](../../shared/record-audits.md)" in skill


def test_native_identity_authority_and_lifecycle_contract() -> None:
    shared = read(SHARED_HANDOFF)
    direction = read(RECORD_MANAGEMENT)
    opportunity = read(OPPORTUNITY_MANAGEMENT)
    audits = read(RECORD_AUDITS)
    for phrase in (
        "immutable resource or file ID",
        "canonical link or durable path",
        "filename, line number",
        "not a durable identity",
        "Career direction defines reusable goals",
        "it is not an opportunity tracker",
        "Opportunity records apply or reference those criteria",
        "Canonical resume artifacts and supporting evidence remain authoritative",
    ):
        assert phrase in shared
    assert "Use the Markdown file itself as the retrieval layer" in direction
    assert "Use the Markdown files as their own retrieval layer" in opportunity
    assert "comparison table in `opportunities-current.md` as the native index" in opportunity
    assert "Do not create a sidecar index" in audits
    for phrase in ("exceeds 8 KiB", "exceeds 16 KiB", "more than 180 days old", "25 material changes"):
        assert phrase in audits
    assert "trigger requires review; it never selects a lifecycle action" in audits


def test_preferences_do_not_silently_override_skill_instructions() -> None:
    shared = read(SHARED_HANDOFF)
    for name in SKILL_NAMES:
        skill = skill_text(name)
        assert "explicit user confirmation" in skill
    assert "not an override of a conflicting skill instruction" in shared
    assert "never weaken factual accuracy, evidence integrity" in shared


def test_career_direction_owns_one_in_place_record() -> None:
    direction = skill_text("career-direction")
    criteria = read(
        SKILLS_ROOT / "career-direction" / "references" / "decision-criteria.md"
    )
    assert "Own bounded durable creation and updates for both" in direction
    assert "Update selected records in place" in direction
    assert "Do not create a skill-local copy" in direction
    assert "discovery-framework.md" in direction
    assert "decision-criteria.md" in direction
    assert "Canonical record structure" in criteria
    assert not list(PLUGIN_ROOT.rglob("career_direction_record.md"))
    assert not list(PLUGIN_ROOT.rglob("career_direction_history.md"))
    assert not list(PLUGIN_ROOT.rglob("career-coach-preferences.md"))
    assert not list(PLUGIN_ROOT.rglob("opportunities-current.md"))
    assert not list(PLUGIN_ROOT.rglob("opportunities-history.md"))


def test_consumer_skills_search_record_without_owning_copies() -> None:
    for name in ("evaluate-opportunity", "update-resume"):
        skill = skill_text(name)
        assert "Read it first" in skill
        assert "Do not create or maintain a separate direction record" in skill
        assert "bounded in-place update" in skill


def test_shared_handoffs_preserve_record_identity_and_evidence_limits() -> None:
    shared = read(SHARED_HANDOFF)
    for heading in (
        "Career Direction to Evaluate Opportunity",
        "Evaluate Opportunity to Career Direction",
        "Career Direction to Update Resume",
        "Update Resume to Career Direction",
    ):
        assert heading in shared
    assert "exact working-record identity" in shared
    assert "cannot establish an unverified resume claim" in shared
    assert "Never create skill-local static copies" in shared


def test_two_tier_authority_and_retrieval_contract() -> None:
    shared = read(SHARED_HANDOFF)
    detail = read(RECORD_MANAGEMENT)
    assert "sole authority for current career direction" in shared
    assert "authoritative only about historical state" in shared
    assert "working record governs" in shared
    assert "Semantic or keyword retrieval does not enforce" in shared
    assert "Do not load the complete archive" in shared
    assert "retrieval miss is not evidence that history does not exist" in shared
    assert "H-YYYY-MM-DD-NN" in shared and "H-YYYY-MM-DD-NN" in detail
    for status in ("superseded", "archived", "rejected", "restored"):
        assert status in detail


def test_record_reference_defines_schema_lifecycle_migration_and_failures() -> None:
    detail = read(RECORD_MANAGEMENT)
    for heading in (
        "## Canonical pair",
        "## Working-record schema",
        "## Historical-record schema",
        "## Pointers",
        "## Targeted retrieval",
        "## Coherent update lifecycle",
        "## Migration",
        "## Coherence validation",
        "## Failure behavior",
    ):
        assert heading in detail
    for phrase in (
        "effective date",
        "replacement or restoration relationship",
        "Promote",
        "Demote",
        "Invalidate",
        "Remove",
        "Restore",
        "do not claim persistence succeeded",
    ):
        assert phrase in detail


def test_record_management_eval_has_required_case_contracts() -> None:
    suite = json.loads(read(PLUGIN_ROOT / "evals" / "record-management.json"))
    cases = {case["id"]: case for case in suite["cases"]}
    assert set(cases) == {
        "routine-working-only",
        "opportunity-current-context-only",
        "targeted-historical-question",
        "working-overrides-superseded",
        "material-criterion-change",
        "restore-archived-criterion",
        "broken-historical-pointer",
        "duplicate-candidate-records",
        "historical-retrieval-miss",
        "partial-write-access",
        "downstream-history-exclusion",
        "existing-behavior-regression",
    }
    for case in cases.values():
        assert case["expected_files_read"]
        assert isinstance(case["forbidden_files_read"], list)
        assert case["authoritative_result"]
        assert isinstance(case["permitted_writes"], list)
        assert case["failure_criteria"]


def test_regression_suite_covers_shared_record_behaviors() -> None:
    suite = json.loads(read(PLUGIN_ROOT / "evals" / "regression.json"))
    case_ids = {case["id"] for case in suite["cases"]}
    assert {
        "shared-direction-record",
        "direction-update-handoff",
        "preference-file-conflict",
    }.issubset(case_ids)


def test_opportunity_pair_authority_ownership_and_access() -> None:
    shared = read(SHARED_HANDOFF)
    detail = read(OPPORTUNITY_MANAGEMENT)
    evaluate = skill_text("evaluate-opportunity")
    assert "sole authority for active opportunities" in shared
    assert "authoritative only about inactive or prior opportunity state" in shared
    assert "`evaluate-opportunity` owns creation and bounded durable updates" in shared
    assert "All Career Coach skills may read relevant current entries" in shared
    assert "Own bounded durable creation and updates" in evaluate
    for name in ("career-direction", "update-resume"):
        skill = skill_text(name)
        assert "Do not create or update opportunity records directly" in skill
    assert "Do not create skill-local copies" in detail


def test_opportunity_reference_defines_schema_lifecycle_and_failures() -> None:
    detail = read(OPPORTUNITY_MANAGEMENT)
    for heading in (
        "## Canonical pair",
        "## Opportunity-description files",
        "## Current-record schema",
        "## Ranked current-state table",
        "## Historical-record schema",
        "## Stable identities and pointers",
        "## Targeted retrieval",
        "## Lifecycle",
        "## Coherence validation",
        "## Failure behavior",
    ):
        assert heading in detail
    for phrase in (
        "O-YYYY-MM-DD-NN",
        "OH-YYYY-MM-DD-NN",
        "Open",
        "Advance",
        "Revise",
        "Close",
        "Reopen",
        "Remove",
        "do not imply persistence succeeded",
    ):
        assert phrase in detail


def test_opportunity_posting_filename_and_authority_contract() -> None:
    shared = read(SHARED_HANDOFF)
    detail = read(OPPORTUNITY_MANAGEMENT)
    evaluate = skill_text("evaluate-opportunity")
    expected_name = "O-YYYY-MM-DD-NN -- Employer -- Role.md"
    assert expected_name in detail
    assert "two ASCII hyphens (`--`)" in detail
    assert "never use em dashes as filename separators" in detail
    assert "Sanitize only characters invalid for the target filesystem" in detail
    assert "without summarizing, silently correcting, embellishing" in detail
    assert "authoritative only for full posting text or an explicitly authorized" in shared
    assert "canonical captured-posting files" in evaluate
    assert "Google Drive folder named `opportunity descriptions`, `job descriptions`" in detail
    assert "store each posting file directly in the selected library location" in detail
    assert "filename and exact resolvable location" in shared
    assert "source website" in shared
    assert "Use the captured file, not the live website" in shared


def test_posting_privacy_and_summary_authorization_contract() -> None:
    shared = read(SHARED_HANDOFF)
    detail = read(OPPORTUNITY_MANAGEMENT)
    evaluate = skill_text("evaluate-opportunity")
    for phrase in (
        "Never include user- or candidate-specific information",
        "the user's name, personal contact details or other user identifiers",
        "resume evidence",
        "career preferences or constraints",
        "candidate-to-role or role-to-candidate fit",
        "Employer or recruiter details present in the source posting",
        "reject a proposed canonical posting file",
        "(1) supply the full job-description text",
        "(2) authorize `evaluate-opportunity` to save a source-grounded summary",
        "do not create or replace the canonical posting file",
    ):
        assert phrase in detail
    assert "Never place resume evidence, personal experience, preferences" in shared
    assert "Never save a summary before that authorization" in evaluate

    suite = json.loads(read(PLUGIN_ROOT / "evals" / "opportunity-record-management.json"))
    cases = {case["id"]: case for case in suite["cases"]}
    rejected = cases["reject-user-identifiable-posting"]
    assert "rejects the mixed-content file" in rejected["authoritative_result"]
    assert any(
        "contaminated file is accepted" in criterion
        for criterion in rejected["failure_criteria"]
    )
    assert all(
        "canonical posting" not in write or "no canonical posting write" in write
        for write in rejected["permitted_writes"]
    )


def test_ranked_opportunity_table_and_salary_contract() -> None:
    detail = read(OPPORTUNITY_MANAGEMENT)
    header = (
        "| Rank | Opportunity ID | Employer | Role | Annualized salary range | "
        "Candidate-to-role fit | Role-to-candidate fit | Status | Next action | "
        "Last updated |"
    )
    assert header in detail
    for phrase in (
        "user's explicit ranking or an explicit authoritative ranking rule",
        "Use `Unranked` when no rank is confirmed",
        "order them by opportunity identifier",
        "show the calculation assumption",
        "Never present calculated annualization as employer-stated compensation",
        "rather than percentages or an undeclared numeric scoring model",
    ):
        assert phrase in detail


def test_opportunity_handoffs_preserve_boundaries() -> None:
    shared = read(SHARED_HANDOFF)
    for heading in (
        "Evaluate Opportunity to Update Resume",
        "Update Resume to Evaluate Opportunity",
        "Career Direction to Evaluate Opportunity Records",
        "Evaluate Opportunity Records to Career Direction",
    ):
        assert heading in shared
    assert "cannot establish an unverified resume claim" in shared
    assert "must not create, update, or keep parallel opportunity records" in shared


def test_opportunity_record_eval_has_required_case_contracts() -> None:
    suite = json.loads(read(PLUGIN_ROOT / "evals" / "opportunity-record-management.json"))
    cases = {case["id"]: case for case in suite["cases"]}
    assert set(cases) == {
        "open-real-opportunity",
        "capture-complete-posting",
        "capture-unavailable-posting-choice",
        "capture-user-supplies-full-text-choice",
        "capture-authorized-third-party-summary",
        "capture-posting-excludes-candidate-context",
        "reject-user-identifiable-posting",
        "capture-library-fallback",
        "clarify-from-captured-posting",
        "sanitize-posting-filename",
        "rank-current-opportunities",
        "annualize-salary-with-assumption",
        "revise-canonical-posting",
        "advance-current-state",
        "close-declined-opportunity",
        "reopen-opportunity",
        "resume-consumer-read-only",
        "direction-consumer-bounded-handoff",
        "partial-opportunity-write",
        "duplicate-opportunity-records",
    }
    for case in cases.values():
        assert case["expected_files_read"]
        assert isinstance(case["forbidden_files_read"], list)
        assert case["authoritative_result"]
        assert isinstance(case["permitted_writes"], list)
        assert case["failure_criteria"]


def load_audit_module():
    spec = importlib.util.spec_from_file_location("career_record_audit", AUDIT_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_audit_fixture(tmp_path: Path):
    module = load_audit_module()
    tmp_path.mkdir(parents=True, exist_ok=True)
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    (before / "postings").mkdir()
    files = {
        "career_direction_record.md": """# Career direction\n\n## Requirements and non-negotiables\nMinimum base compensation: USD $225,000\nMaximum routine travel: 10%\nSource: user-confirmed 2026-08-16\nConsult career_direction_history.md entry H-2026-08-16-01 only when reviewing compensation.\nRedundant heading wording.\n""",
        "career_direction_history.md": """# Direction history\n\n## H-2026-08-16-01\nSuperseded compensation: USD $200,000\nStatus: superseded\n""",
        "opportunities-current.md": """# Current opportunities\n\n| Rank | Opportunity ID | Employer | Role | Status | Next action | Last updated |\n| --- | --- | --- | --- | --- | --- | --- |\n| 1 | O-2026-08-16-01 | Example Co | COO | interviewing | Prepare case study | 2026-08-16 |\n\n## O-2026-08-16-01 -- Example Co -- COO\nDeadline: 2026-08-31\nPosting: postings/O-2026-08-16-01 -- Example Co -- COO.md\n""",
        "opportunities-history.md": """# Opportunity history\n\n## OH-2026-08-15-01\nRelated opportunity: O-2026-08-16-01\nStatus: superseded\n""",
        "postings/O-2026-08-16-01 -- Example Co -- COO.md": """# COO posting\n\nOpportunity ID: O-2026-08-16-01\nSource URL: https://example.test/jobs/1\nCaptured: 2026-08-16\nComplete: true\n""",
    }
    for relative, contents in files.items():
        path = before / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    shutil.copytree(before, after)
    direction_after = after / "career_direction_record.md"
    direction_after.write_text(
        direction_after.read_text(encoding="utf-8").replace("Redundant heading wording.\n", ""),
        encoding="utf-8",
    )

    before_items = [
        {"id": "b-authority", "kind": "authority", "path": "career_direction_record.md", "text": "# Career direction"},
        {"id": "b-comp", "kind": "exact_constraint", "path": "career_direction_record.md", "text": "Minimum base compensation: USD $225,000"},
        {"id": "b-travel", "kind": "numeric_rule", "path": "career_direction_record.md", "text": "Maximum routine travel: 10%"},
        {"id": "b-direction-source", "kind": "provenance", "path": "career_direction_record.md", "text": "Source: user-confirmed 2026-08-16"},
        {"id": "b-direction-pointer", "kind": "pointer", "path": "career_direction_record.md", "text": "Consult career_direction_history.md entry H-2026-08-16-01 only when reviewing compensation.", "target_path": "career_direction_history.md", "target_text": "H-2026-08-16-01"},
        {"id": "b-history-id", "kind": "stable_id", "namespace": "direction-history", "path": "career_direction_history.md", "text": "H-2026-08-16-01"},
        {"id": "b-opp-id", "kind": "stable_id", "namespace": "opportunity-current", "path": "opportunities-current.md", "text": "O-2026-08-16-01"},
        {"id": "b-rank", "kind": "numeric_rule", "path": "opportunities-current.md", "text": "| 1 | O-2026-08-16-01 | Example Co | COO | interviewing | Prepare case study | 2026-08-16 |"},
        {"id": "b-deadline", "kind": "exact_constraint", "path": "opportunities-current.md", "text": "Deadline: 2026-08-31"},
        {"id": "b-posting-pointer", "kind": "pointer", "path": "opportunities-current.md", "text": "Posting: postings/O-2026-08-16-01 -- Example Co -- COO.md", "target_path": "postings/O-2026-08-16-01 -- Example Co -- COO.md", "target_text": "Opportunity ID: O-2026-08-16-01"},
        {"id": "b-oh-id", "kind": "stable_id", "namespace": "opportunity-history", "path": "opportunities-history.md", "text": "OH-2026-08-15-01"},
        {"id": "b-posting-source", "kind": "provenance", "path": "postings/O-2026-08-16-01 -- Example Co -- COO.md", "text": "Source URL: https://example.test/jobs/1"},
        {"id": "b-redundant", "kind": "redundant_wording", "path": "career_direction_record.md", "text": "Redundant heading wording."},
    ]
    after_items = []
    decisions = []
    for item in before_items:
        if item["id"] == "b-redundant":
            decisions.append({"before_id": item["id"], "disposition": "removed", "after_ids": [], "justification": "Valueless duplicate wording."})
            continue
        target = dict(item)
        target["id"] = item["id"].replace("b-", "a-", 1)
        after_items.append(target)
        decisions.append({"before_id": item["id"], "disposition": "retained", "after_ids": [target["id"]]})
    ledger = {
        "schema_version": 1,
        "current_state_review": "passed",
        "history_reconstruction_review": "passed",
        "cross_authority_review": "passed",
        "before_files": module.markdown_inventory(before),
        "after_files": module.markdown_inventory(after),
        "before_items": before_items,
        "after_items": after_items,
        "decisions": decisions,
        "new_after_ids": [],
    }
    return module, before, after, ledger


def test_record_audit_completes_and_preserves_protected_state(tmp_path: Path) -> None:
    module, before, after, ledger = build_audit_fixture(tmp_path)
    module.validate_audit(before, after, ledger)
    assert "USD $225,000" in read(after / "career_direction_record.md")
    assert "Maximum routine travel: 10%" in read(after / "career_direction_record.md")
    assert "O-2026-08-16-01" in read(after / "opportunities-current.md")
    assert "Source URL: https://example.test/jobs/1" in read(after / "postings" / "O-2026-08-16-01 -- Example Co -- COO.md")


def test_record_audit_failures_leave_before_state_unchanged(tmp_path: Path) -> None:
    for label in ("omitted", "changed", "duplicate", "broken-pointer"):
        module, before, after, bad_ledger = build_audit_fixture(tmp_path / label)
        before_hashes = module.markdown_inventory(before)
        if label == "omitted":
            bad_ledger["decisions"] = [
                decision for decision in bad_ledger["decisions"] if decision["before_id"] != "b-travel"
            ]
            expected_error = "Every before item"
        elif label == "changed":
            changed_path = after / "career_direction_record.md"
            changed_path.write_text(read(changed_path).replace("USD $225,000", "USD $230,000"), encoding="utf-8")
            bad_ledger["after_files"] = module.markdown_inventory(after)
            next(item for item in bad_ledger["after_items"] if item["id"] == "a-comp")["text"] = "Minimum base compensation: USD $230,000"
            expected_error = "changed kind or text"
        elif label == "duplicate":
            duplicate_item = dict(next(item for item in bad_ledger["after_items"] if item["id"] == "a-opp-id"))
            duplicate_item["id"] = "a-opp-id-duplicate"
            bad_ledger["after_items"].append(duplicate_item)
            bad_ledger["new_after_ids"].append(duplicate_item["id"])
            bad_ledger["new_items_justification"] = "Test duplicate."
            expected_error = "Duplicate stable ID"
        else:
            next(item for item in bad_ledger["after_items"] if item["id"] == "a-direction-pointer")["target_text"] = "H-2099-01-01-99"
            expected_error = "Broken pointer target"
        try:
            module.validate_audit(before, after, bad_ledger)
        except module.AuditError as exc:
            assert expected_error in str(exc)
        else:
            raise AssertionError("Unsafe audit unexpectedly passed")
        assert module.markdown_inventory(before) == before_hashes


def test_record_audit_eval_has_required_cases() -> None:
    suite = json.loads(read(PLUGIN_ROOT / "evals" / "record-audits.json"))
    cases = {case["id"] for case in suite["cases"]}
    assert {
        "direction-audit-due",
        "opportunity-audit-due",
        "successful-cross-record-audit",
        "direction-opportunity-authority-conflict",
        "changed-protected-constraint",
        "duplicate-opportunity-id",
        "broken-posting-pointer",
        "resume-evidence-boundary",
    } == cases
