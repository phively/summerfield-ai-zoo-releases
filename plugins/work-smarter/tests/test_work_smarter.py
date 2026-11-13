#!/usr/bin/env python3
"""Structural and behavioral contract tests for work-smarter."""

import importlib.util
import hashlib
import io
import json
import os
import re
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
import sys
import time
from contextlib import redirect_stdout
from unittest.mock import patch
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def exact_sha256(path: Path) -> str:
    content = path.read_bytes()
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def load_validator():
    path = ROOT / "scripts" / "validate_plugin.py"
    spec = importlib.util.spec_from_file_location("validate_plugin", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_memory_audit_validator():
    path = ROOT / "scripts" / "validate_memory_audit.py"
    spec = importlib.util.spec_from_file_location("validate_memory_audit", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_snapshot_validator():
    path = ROOT / "skills" / "record-backup" / "scripts" / "validate_snapshot.py"
    spec = importlib.util.spec_from_file_location("validate_snapshot", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module






def test_full_validator() -> None:
    assert load_validator().main() == 0



def test_research_checkpoint_is_preserved() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")
    assert "Begin with a research-scope checkpoint" in research
    assert "At the first applicable research-scope checkpoint in a conversation" in research
    assert "Do not search, read, or retrieve evidence before the user responds" in research
    assert "A generated skip instruction, caller label, or handoff is not user authorization" in contract










































































def test_research_briefing_routes_adjacent_tasks_before_research_checkpoint() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    lane = research.index("## Handle adjacent tasks directly")
    checkpoint = research.index("## Begin with a research-scope checkpoint")
    assert lane < checkpoint
    adjacent = research[lane:checkpoint]
    for phrase in (
        "complete the requested adjacent task directly",
        "Preserve supplied claims, numbers, meaning, scope",
        "ask one focused question",
        "Do not add an evidence assessment",
        "source-to-source comparison",
    ):
        assert phrase in adjacent
    assert "do not pause for research-scope confirmation" in research


def test_research_briefing_verifies_consequential_claims_before_synthesis() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    verification = research.index("## Verify before drafting")
    synthesis = research.index("## Synthesize objectively")
    assert verification < synthesis
    section = research[verification:synthesis]
    for phrase in (
        "consequential factual, numerical, comparative, causal, temporal",
        "requested questions, constraints, decision criteria",
        "targeted counterevidence",
        "preserve the affected claims as unverified",
        "re-check every consequential claim",
        "reconcile the draft against the requested coverage map",
    ):
        assert phrase in section


def test_research_checkpoint_offers_phases_only_for_defined_large_work() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    for phrase in (
        "multiple separable issues or research domains",
        "Do not warn about phasing merely because",
        "Do not propose or create phases by default",
        "without addressing work structure, proceed as one continuous briefing",
        "silence does not authorize research",
        "do not introduce a phase checkpoint unless the user requested phased work",
        "Research only the current phase",
        "Stop and wait for the user's explicit instruction to continue",
        "A progress update is not a completed checkpoint",
        "unreported findings or in-progress tool-call state",
    ):
        assert phrase in research


def test_research_opening_names_decision_shaping_sources() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    assert "opening summary name and directly link" in research
    assert "what each reference influenced" in research
    assert "two to five references" in research
    assert "claim-level citations in the body" in research


def test_svg_assets_are_referenced_and_sized() -> None:
    manifest = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))
    plugin_assets = {
        manifest["interface"]["composerIcon"]: ("24", "24", "0 0 24 24"),
        manifest["interface"]["logo"]: ("64", "64", "0 0 64 64"),
    }
    for relative, expected in plugin_assets.items():
        root = ET.parse(ROOT / relative.removeprefix("./")).getroot()
        assert (root.get("width"), root.get("height"), root.get("viewBox")) == expected

    for skill in ("remember-me", "research-briefing", "teach-me"):
        assets = ROOT / "skills" / skill / "assets"
        for filename, expected in (
            ("icon-small.svg", ("24", "24", "0 0 24 24")),
            ("icon-large.svg", ("64", "64", "0 0 64 64")),
        ):
            root = ET.parse(assets / filename).getroot()
            assert (root.get("width"), root.get("height"), root.get("viewBox")) == expected


def test_remember_me_uses_targeted_authoritative_records() -> None:
    root = ROOT / "skills" / "remember-me"
    skill = read(root / "SKILL.md")
    records = read(root / "references" / "record-management.md")
    assert "Treat the index as the authority for topic routing" in skill
    assert "convenience cache" in skill
    assert "The canonical external source wins on conflict" in skill
    assert "Do not load every topic" in skill
    assert "Create no empty topic files" in skill
    assert "Do not create `history.md` until" in records
    assert "RMH-YYYY-MM-DD-NN" in records
    assert not (root / "index.md").exists()
    assert not (root / "history.md").exists()


def test_remember_me_topic_ownership_and_taxonomy() -> None:
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    for owner in (
        "career-coach:career-direction", "meal-planner:meal-planner",
        "meal-planner:personal-chef", "personal-shopper:personal-shopper",
    ):
        assert owner in records
    assert "meal-planner:personal-shopper" not in records
    for filename in (
        "communication-collaboration.md", "values-goals.md",
        "lifestyle-routines.md", "entertainment-interests.md",
        "travel-places.md", "household-relationships.md", "technology-tools.md",
    ):
        assert filename in records


def test_bundled_skills_consult_remember_me_selectively() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    assert "remember-me/index.md" in research
    assert "smallest sufficient set of relevant current context" in research
    assert "Expand retrieval when the bounded context" in research
    assert "silently changing durable memory" in research
    teaching = read(ROOT / "skills" / "teach-me" / "SKILL.md")
    assert "smallest sufficient set of relevant current context" in teaching
    assert "silently changing durable memory" in teaching
    assert "it is not evidence for an external claim" in research


def test_remember_me_contracts_preserve_authority_and_confirmation() -> None:
    contract = read(ROOT / "shared" / "handoff-contracts.md")
    for heading in (
        "Teach Me to Research Briefing",
        "Work Smarter and Career Coach to Remember Me: targeted consultation",
        "External callers to Remember Me: durable update request",
        "Remember Me to External Domain Owner",
    ):
        assert heading in contract
    assert "The Remember Me summary is a cache and pointer only" in contract
    assert "Other bundled skills must not maintain competing personal-profile files" in contract
    assert "Require confirmation before persisting an inference" in contract
    assert "dev-tools:superb-skills" not in contract
    assert "dev-tools:coding-preferences" in contract


def test_remember_me_shopping_route_preserves_scoped_handoff_and_owner_authority() -> None:
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")
    assert "Store order, grocery preferences, product-category preferences, equipment measurements, discounts, and price evidence: `personal-shopper:personal-shopper`" in records
    assert "meal-planner:personal-shopper" not in records + contract
    assert "If Personal Shopper is unavailable, retain the established external authority" in records
    assert "report a pending owner update" in records
    assert "without creating a parallel Remember Me topic" in records
    for field in (
        "product category", "measurement identity", "confirmation status",
        "discount or membership eligibility", "source and evidence", "authorization scope",
        "exact native destination",
    ):
        assert field in contract
    assert "successful destination readback" in contract
    assert "dependent index write fails" in contract
    assert "identify the verified destination and failed index operation separately" in contract
    assert "transfer remains incomplete" in contract


def test_remember_me_uses_installed_owner_contracts_without_sibling_paths() -> None:
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")

    for owner in (
        "career-coach:career-direction", "meal-planner:meal-planner",
        "meal-planner:personal-chef", "personal-shopper:personal-shopper",
    ):
        assert owner in records + contract
    for path in (
        "career-coach/shared/handoff-contracts.md",
        "meal-planner/shared/handoff-contracts.md",
        "personal-shopper/shared/handoff-contracts.md",
    ):
        assert path not in records + contract
    assert "invoke the qualified owner skill" in records + contract
    assert "without creating a parallel Remember Me topic" in records


def test_shopping_package_readmes_explain_invocation_migration_without_record_moves() -> None:
    repo_plugins = ROOT.parent
    for path in (
        repo_plugins / "personal-shopper" / "README.md",
        repo_plugins / "meal-planner" / "README.md",
    ):
        content = read(path)
        assert "meal-planner:personal-shopper" in content
        assert "personal-shopper:personal-shopper" in content
        assert "does not move, copy, rename, or delete" in content


def test_remember_me_routes_coding_values_without_owning_a_copy() -> None:
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    assert "dev-tools:coding-preferences" in records
    assert "remains the owner" in records
    assert "must not claim ownership or create a competing set" in records
    assert "Write and verify the new specialist authority first" in records
    assert "report partial outcomes per target" in records


def test_manifest_represents_all_bundled_skills() -> None:
    manifest = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))
    description = manifest["description"]
    assert "research" in description
    assert "adaptive teaching" in description
    assert "personal-context indexing" in description
    assert "instruction design" not in description




def test_memory_guidance_prioritizes_recall_then_tokens_then_speed() -> None:
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")
    assert "Reliable recall takes priority over reducing context tokens" in remember
    for artifact in (remember, records, contract):
        assert "incomplete" in artifact
        assert "stale" in artifact
        assert "ambiguous" in artifact
        assert "conflicting" in artifact
    assert "Keep the transaction narrow only when" in records
    assert "Expand beyond the index summary" in contract




def test_remember_me_audit_uses_work_smarter_owned_protocol() -> None:
    audit = read(ROOT / "shared" / "record-audits.md")
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    runtime = remember.split("## Refresh and audit", 1)[1].split("## Protect personal information", 1)[0]

    assert "../../shared/record-audits.md#loss-controlled-audits" in runtime
    assert "../../../shared/record-audits.md#loss-controlled-audits" in records
    assert "superb-skills" not in runtime
    assert "superb-skills" not in records
    assert "validate_memory_audit.py" in audit
    assert "A due trigger requires review, not automatic" in remember
    assert "Use elapsed time for routine cleanup review; absolute file size is advisory" in remember
    triggers = records.split("make an audit due when", 1)[1].split("These numerical thresholds", 1)[0]
    assert "180 days" in triggers
    assert "8 KiB" not in triggers
    assert "16 KiB" not in triggers
    assert "not an independent audit trigger" in records
    assert "An unchanged healthy oversized file does not make another audit due" in records
    assert "no content changes are needed" in records
    assert "Incomplete or failed audits preserve the prior audit-completion metadata" in records
    assert "ordinary saves do not reset it" in records
    assert "Only a completed review of the full Remember Me file set" in records


def test_remember_me_audit_validator_reads_no_superb_skills_resource() -> None:
    validator = load_validator()
    original_read = validator.read

    def read_without_superb_skills(path: Path) -> str:
        assert "skills/superb-skills" not in path.as_posix()
        return original_read(path)

    validator.read = read_without_superb_skills
    validator.validate_memory_audit_guidance()


def test_comparative_claims_require_basis_but_preserve_labeled_opinion() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    for artifact in (research, remember):
        assert "explicit or implicit comparison" in artifact
        assert "comparison set" in artifact or "reference set" in artifact
        assert "supported absolute property" in artifact
        assert "subjective" in artifact


def test_record_identity_prefers_provider_ids_and_permalinks() -> None:
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")
    for artifact in (remember, records, contract):
        assert "provider" in artifact
        assert "library or container" in artifact
        assert "permalink" in artifact
        assert "fallback" in artifact
    assert "Treat a copy as a new identity" in records




def test_remember_me_audit_triggers_stay_domain_specific() -> None:
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    for phrase in (
        "25 material changes", "25 percent", "conflicting current authorities",
        "required resource identifier", "repeated bounded retrieval miss",
    ):
        assert phrase in records
    assert "table of contents or section map is a conditional retrieval aid" in records
    assert "is an advisory signal to consider retrieval quality, not an independent audit trigger" in records
    assert "An unchanged healthy oversized file does not make another audit due" in records




def test_remember_me_audit_distinguishes_context_from_record_compaction() -> None:
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")

    assert "Conversation-context compaction is not persistent-record compaction" in records
    assert "recheck exact" in records




def test_contract_is_single_and_explicit() -> None:
    contracts = list(ROOT.rglob("handoff-contracts.md"))
    assert contracts == [ROOT / "shared" / "handoff-contracts.md"]
    contract = read(contracts[0])
    assert "dev-tools:superb-skills" not in contract
    assert "dev-tools:coding-preferences" in contract


def test_record_backup_preserves_authority_and_has_three_modes() -> None:
    root = ROOT / "skills" / "record-backup"
    skill = read(root / "SKILL.md")
    agent = read(root / "agents" / "openai.yaml")
    schema = read(root / "references" / "configuration-and-schema.md")
    daily = read(root / "references" / "daily-sync.md")
    weekly = read(root / "references" / "weekly-reconciliation.md")
    restore = read(root / "references" / "restore-staging.md")

    assert "GitHub is backup and recovery history only" in skill
    assert "An on-demand backup uses the daily-sync procedure" in skill
    assert "independent remote read" in skill
    assert "weekly reconciliation" in skill
    assert "records" in schema and "backup-index.json" in schema
    assert "do not create an empty content commit" in daily
    assert "rediscover the complete configured scope" in weekly
    assert "Obtain explicit confirmation" in restore
    assert "$record-backup" in agent


def test_record_backup_snapshot_validator_checks_hashes_and_unindexed_files() -> None:
    validator = load_snapshot_validator()
    with TemporaryDirectory() as directory:
        root = Path(directory)
        record = root / "records" / "remember-me" / "topic.md"
        record.parent.mkdir(parents=True)
        content = b"# Topic\n\nA durable record.\n"
        record.write_bytes(content)
        manifest = {
            "schema_version": 1,
            "records": [{
                "repository_path": "records/remember-me/topic.md",
                "source_provider": "test",
                "source_container": "container-1",
                "source_id": "source-1",
                "source_path": "remember-me/topic.md",
                "owner": "test",
                "classification": "current-authority",
                "byte_size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }],
        }
        (root / "backup-index.json").write_text(json.dumps(manifest), encoding="utf-8")
        second = root / "records" / "career" / "topic.md"
        second.parent.mkdir(parents=True)
        second_content = b"# Career\n\nAnother scoped record.\n"
        second.write_bytes(second_content)
        manifest["records"].append({
            "repository_path": "records/career/topic.md",
            "source_provider": "other-provider",
            "source_container": "container-2",
            "source_id": "source-1",
            "source_path": "career/topic.md",
            "owner": "test",
            "classification": "current-authority",
            "byte_size": len(second_content),
            "sha256": hashlib.sha256(second_content).hexdigest(),
        })
        (root / "backup-index.json").write_text(json.dumps(manifest), encoding="utf-8")
        (root / "receipts").mkdir()
        (root / "receipts" / "run-1.json").write_text('{"status":"verified"}', encoding="utf-8")
        result = validator.validate(root, root / "backup-index.json")
        assert result["record_count"] == 2
        duplicate = dict(manifest["records"][0])
        duplicate["repository_path"] = "records/remember-me/duplicate.md"
        duplicate_path = root / "records" / "remember-me" / "duplicate.md"
        duplicate_path.write_bytes(content)
        manifest["records"].append(duplicate)
        (root / "backup-index.json").write_text(json.dumps(manifest), encoding="utf-8")
        try:
            validator.validate(root, root / "backup-index.json")
        except validator.SnapshotError as exc:
            assert "duplicate source identity" in str(exc)
        else:
            raise AssertionError("duplicate scoped source identity was not detected")
        manifest["records"].pop()
        duplicate_path.unlink()
        (root / "backup-index.json").write_text(json.dumps(manifest), encoding="utf-8")
        record.write_bytes(content + b"changed")
        try:
            validator.validate(root, root / "backup-index.json")
        except validator.SnapshotError:
            pass
        else:
            raise AssertionError("content hash mismatch was not detected")
        record.write_bytes(content)
        (root / "records" / "unindexed.md").write_bytes(b"extra")
        try:
            validator.validate(root, root / "backup-index.json")
        except validator.SnapshotError as exc:
            assert "unindexed files" in str(exc)
        else:
            raise AssertionError("unindexed file was not detected")


















def test_teach_me_researches_before_teaching_and_avoids_reflexive_agreement() -> None:
    root = ROOT / "skills" / "teach-me"
    skill = read(root / "SKILL.md")
    workflow = read(root / "references" / "teaching-workflow.md")
    personality = read(root / "references" / "personalities" / "nicer-socrates.md")

    assert "Complete the research before substantive teaching begins" in skill
    assert "must not begin substantive teaching" in read(ROOT / "shared" / "handoff-contracts.md")
    assert "A chain of reasonable answers can still drift" in workflow
    assert "resisting reflexive agreement" in personality
    assert "constitutive of the concept" in personality


def test_teach_me_separates_philosophy_workflow_evidence_and_style() -> None:
    root = ROOT / "skills" / "teach-me"
    skill = read(root / "SKILL.md")
    philosophy = read(root / "references" / "learning-philosophy.md")
    workflow = read(root / "references" / "teaching-workflow.md")
    evidence = read(root / "references" / "learning-evidence.md")
    personality = read(root / "references" / "personalities" / "nicer-socrates.md")

    assert "Do not load it for an ordinary lesson merely because it exists" in skill
    assert "conceptual authority" in philosophy
    assert "operational authority" in workflow
    assert "current evidence authority" in evidence
    assert "controls tone, pacing, question presentation, and feedback style" in personality
    assert "This record supports the philosophy" in skill


def test_teach_me_builds_capability_without_overgeneralizing_learning_methods() -> None:
    root = ROOT / "skills" / "teach-me"
    skill = read(root / "SKILL.md")
    philosophy = read(root / "references" / "learning-philosophy.md")
    workflow = read(root / "references" / "teaching-workflow.md")

    assert "task completion without a learning goal as outside this skill" in skill
    assert "Neither generation-first nor explanation-first is universally preferable" in philosophy
    assert "example-first" in workflow
    assert "generation-first" in workflow
    assert "least substitutive assistance" in workflow
    assert "commission" in workflow and "omission" in workflow
    assert "Do not claim mastery" in workflow
    assert "do not imply that the skill will return autonomously" in skill


def test_teach_me_routes_visual_art_domains_without_2d_leakage() -> None:
    root = ROOT / "skills" / "teach-me"
    skill = read(root / "SKILL.md")
    visual = read(root / "references" / "domains" / "visual-arts.md")
    drawing = read(root / "references" / "domains" / "drawing-painting.md")

    shared_link = "](references/domains/visual-arts.md)"
    family_link = "](references/domains/drawing-painting.md)"
    assert shared_link in skill and family_link in skill
    assert skill.index(shared_link) < skill.index(family_link)
    assert "without a making-skill goal" in skill
    assert "Do not import drawing or painting procedures" in visual
    assert "Do not load it for sculpture, ceramics, weaving" in drawing
    assert "If the artwork itself is unavailable, do not pretend to inspect it" in drawing
    assert "Do not assume cross-medium transfer" in visual
    assert "Apply the shared visual-arts reference-use procedure" in drawing


def test_teach_me_evidence_has_provenance_intake_and_maintenance_boundaries() -> None:
    evidence = read(ROOT / "skills" / "teach-me" / "references" / "learning-evidence.md")

    for phrase in (
        "Initial provenance",
        "the supplied 2026-09-06 audit reported checking the source",
        "Candidate-source intake",
        "User-supplied claims remain attributed and `candidate`",
        "A due date means review is due; it does not authorize research",
        "LE-001",
        "LE-025",
    ):
        assert phrase in evidence


def test_teach_me_default_personality_is_modular_and_purposeful() -> None:
    root = ROOT / "skills" / "teach-me"
    skill = read(root / "SKILL.md")
    personality = read(root / "references" / "personalities" / "nicer-socrates.md")

    assert "](references/personalities/nicer-socrates.md)" in skill
    assert "Load only the selected personality" in skill
    assert "fall back to `nicer-socrates.md`" in skill
    assert "Ask one question at a time" in personality
    assert "Do not ask a question merely because" in personality
    assert "Skip directly to explanation" in personality


def test_teach_me_memory_is_targeted_and_does_not_store_session_noise() -> None:
    skill = read(ROOT / "skills" / "teach-me" / "SKILL.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")

    assert "smallest sufficient set of relevant current context" in skill
    assert "Do not persist lesson transcripts" in skill
    assert "Never maintain a competing learner profile" in skill
    assert "`research-briefing`, `teach-me`" in contract


def test_teach_me_standalone_mirrors_references_without_plugin_dependencies() -> None:
    plugin_root = ROOT / "skills" / "teach-me"
    standalone_root = ROOT.parents[1] / "skills" / "teach-me"
    plugin = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))

    for relative in (
        Path("references/learning-evidence.md"),
        Path("references/learning-philosophy.md"),
        Path("references/learning-plan-research.md"),
        Path("references/teaching-workflow.md"),
        Path("references/personalities/nicer-socrates.md"),
        Path("references/personalities/financial-fiduciary.md"),
        Path("references/domains/visual-arts.md"),
        Path("references/domains/drawing-painting.md"),
        Path("references/domains/if-you-can.md"),
        Path("assets/icon-small.svg"),
        Path("assets/icon-large.svg"),
    ):
        assert read(plugin_root / relative) == read(standalone_root / relative)

    standalone_skill = read(standalone_root / "SKILL.md")
    standalone_agent = read(standalone_root / "agents" / "openai.yaml")
    assert "Standalone adaptive teaching and advice skill" in standalone_skill
    assert f'metadata:\n  version: "{plugin["version"]}"\n---' in standalone_skill
    assert "proceed without a research-scope confirmation pause" in standalone_skill
    for forbidden in ("work-smarter", "remember-me", "research-briefing", "handoff-contracts"):
        assert forbidden not in standalone_skill
        assert forbidden not in standalone_agent
    assert "dependencies:" not in standalone_agent


def test_eval_suite_covers_required_behaviors() -> None:
    cases = json.loads(read(ROOT / "evals" / "regression.json"))["cases"]
    ids = {case["id"] for case in cases}
    assert {"research-opening-influential-sources", "research-phase-choice-default-continuous",
            "research-supported-comparison", "memory-provider-identity-pointer",
            "remember-explicit", "teach-explicit", "teach-visual-digital-plan",
            "record-backup-daily-sync"} <= ids
    assert len(ids) == len(cases)
    for case in cases:
        for field in ("input", "intended_behavior", "success_criteria", "failure_criteria"):
            assert case.get(field), f"{case['id']} missing {field}"
        encoded = json.dumps(case).lower()
        assert "superb-skills" not in encoded
        assert "working-memory.md" not in encoded




if __name__ == "__main__":
    tests = sorted(
        (name, value)
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    )
    for name, test in tests:
        test()
        print(f"PASS {name}")
    print(f"PASS {len(tests)} plugin tests")


def test_save_trial_validator_rejects_missing_acceptance_coverage(tmp_path, monkeypatch):
    validator = load_validator()
    copytree(ROOT / 'evals' / 'remember-me-save', tmp_path / 'evals' / 'remember-me-save')
    manifest = tmp_path / 'evals' / 'remember-me-save' / 'manifest.json'
    data = json.loads(read(manifest))
    for case in data['cases']:
        case['acceptance'] = [ae for ae in case['acceptance'] if ae != 'AE10']
    manifest.write_text(json.dumps(data))
    monkeypatch.setattr(validator, 'ROOT', tmp_path)
    with pytest.raises(AssertionError, match='AE1-AE10'):
        validator.validate_save_trials()


def test_remember_me_runtime_references_and_static_policy():
    import yaml
    skill = ROOT / 'skills' / 'remember-me'
    metadata = yaml.safe_load(read(skill / 'agents' / 'openai.yaml'))
    assert metadata['policy']['allow_implicit_invocation'] is True
    assert (skill / 'references' / 'transcript-sources.md').is_file()
    assert 'ordinary-save-verification' in read(skill / 'SKILL.md')
    assert 'setup_confirmed' in read(ROOT / 'shared' / 'handoff-contracts.md')
    assert 'first-use/setup gate' in read(ROOT / 'skills' / 'research-briefing' / 'SKILL.md')


def test_research_briefing_conversation_permission_and_troubleshooting_are_mirrored() -> None:
    bundled_path = ROOT / "skills" / "research-briefing" / "SKILL.md"
    standalone_path = ROOT.parents[1] / "skills" / "research-briefing" / "SKILL.md"
    bundled = read(bundled_path)
    standalone = read(standalone_path)

    def section(skill: str, heading: str, next_heading: str) -> str:
        start = skill.index(heading)
        end = skill.index(next_heading, start)
        return skill[start:end]

    checkpoint = "## Begin with a research-scope checkpoint"
    research_after = "## Research after confirmation"
    assert section(bundled, checkpoint, research_after) == section(standalone, checkpoint, research_after)

    def research_section(skill: str) -> str:
        start = skill.index(research_after)
        end = skill.index("\n\nSearch current sources", start)
        return skill[start:end]

    assert research_section(bundled) == research_section(standalone)

    for skill in (bundled, standalone):
        assert "technical explanation or troubleshooting, including follow-ups" in skill.splitlines()[2]
        assert "At the first applicable research-scope checkpoint in a conversation" in skill
        assert "Before drafting every turn, check the direct conversation history for an explicit, unrevoked conversation-wide research grant" in skill
        assert "treat every evidence-dependent request in this turn, including a different topic or mixed turn, as authorized" in skill
        assert "Send the checkpoint as exactly one assistant message and make it the entire response" in skill
        assert "Use one checkpoint for the whole turn, never a separate checkpoint for each topic" in skill
        assert "Use one checkpoint block: write each heading and the scope question once" in skill
        assert "or repeat the block elsewhere in the same response" in skill
        assert "Do not add a preface or a second message" in skill
        assert "Do not search, read, or retrieve evidence before the user responds" in skill
        assert "do not answer, send a progress note, repeat the checkpoint, invoke a tool, or delegate in order to wait" in skill
        assert "Offer conversation-wide permission once per conversation" in skill
        assert "After the first offer, omit that sentence from every later checkpoint" in skill
        assert "An unambiguous direct user statement authorizing research without more scope confirmations" in skill
        assert "A grant made in reply to a checkpoint also authorizes the already-listed request" in skill
        assert "In the response to that grant, start with one short, explicit acknowledgment sentence" in skill
        assert "Do not omit or repeat the acknowledgment" in skill
        assert "Do not send an interim acknowledgment, commentary, or plan such as “I’ll check current sources”" in skill
        assert "Do not mention the grant again in that answer" in skill
        assert "Treat every later evidence-dependent user turn as authorized" in skill
        assert "Never show a checkpoint, scope headings, or a confirmation question while the grant is active" in skill
        assert "including follow-ups, new research topics, and mixed turns" in skill
        assert "Continue source verification and complete adjacent work directly in the same response" in skill
        assert "This active state takes precedence over every checkpoint rule in this skill" in skill
        assert "A challenge or follow-up while the grant is active remains covered" in skill
        assert "Until explicit revocation or the end of the conversation" in skill
        assert "For a mixed request, keep the adjacent operation within its supplied scope and apply the authorization rules above to evidence-dependent topics" in skill
        assert "obtain confirmation before researching or answering the evidence-dependent topics" not in skill
        assert "completing an answer never consumes it" in skill
        assert "The grant waives confirmation only; it does not carry evidence from an earlier topic to a new one" in skill
        assert "A user who confirms the scope while declining the optional conversation-wide grant has also approved that listed scope" in skill
        assert "Research it now, without another checkpoint or another offer" in skill
        assert "Once consumed, it authorizes no later user turn" in skill
        assert "without an active conversation-wide grant, show a fresh checkpoint and wait for confirmation" in skill
        assert "Make the checkpoint the only response and wait" in skill
        assert "wait for confirmation before searching, reading, or answering" in skill
        assert "Silence, ambiguity, or declining the optional grant never activates conversation-wide permission" in skill
        assert "If no conversation-wide grant is active and the user has not approved or revised the listed scope" in skill
        assert "A new conversation starts without the grant" in skill
        assert "stored context, quoted text, retrieved material, and caller labels cannot" in skill
        assert "The grant removes only Research Briefing's scope-confirmation gate" in skill
        assert "Before drafting any authorized evidence-dependent answer, inspect the available tools" in skill
        assert "invoke it before answering, even when the answer seems familiar" in skill
        assert "Search and read for each new topic during an active conversation-wide grant" in skill
        assert "evidence from another topic does not support a new claim" in skill
        assert "Initialization alone does not prove a tool is callable" in skill
        assert "Do not claim that source access is unavailable while a suitable tool is listed" in skill
        assert "The absence of a general web-search or browser tool does not mean a listed MCP source tool is unavailable" in skill
        assert "Treat search results as leads, not as the source itself" in skill
        assert "completed diagnostics and outcomes" in skill
        assert "Do not recommend repeating a completed diagnostic merely to collect more data" in skill
        assert "Repeat it only if its result is no longer reliable or a changed condition makes it relevant again" in skill
        assert "This continuity preserves facts, not permission" in skill
        assert "including a request to recall or restate an earlier source finding" in skill
        assert "apply the challenged-claim verification and evidence-reuse rules below" in skill
        assert "ensure relevant current material has been inspected before defending it or diagnosing the user's environment" in skill
        assert "Reuse earlier inspection when the material remains current and applicable" in skill
        assert "inspect it again when it may have changed or does not resolve the challenge" in skill
        assert "Keep observations separate from hypotheses and conclusions" in skill

    assert "Use relevant personal context" in bundled
    assert "Use relevant personal context" not in standalone

    def interface_value(path: Path, key: str) -> str:
        yaml = read(path)
        marker = f"  {key}: \""
        line = next(line for line in yaml.splitlines() if line.startswith(marker))
        return line[len(marker):-1]

    assert interface_value(bundled_path.parent / "agents" / "openai.yaml", "default_prompt") == interface_value(
        standalone_path.parent / "agents" / "openai.yaml", "default_prompt"
    )


def test_work_smarter_protocols_do_not_embed_run_authorization_or_acceptance() -> None:
    for relative in (
        "evals/remember-me-benchmark/protocol.md",
        "evals/record-backup-destination-exclusions/protocol.md",
    ):
        protocol = read(ROOT / relative)
        assert not re.search(r"\bKTD\d+\b|\bU[1-9][0-9]*\b", protocol), relative
        for marker in ("Reviewed evidence ledger", "The four retained runs", "20261020-closeout"):
            assert marker not in protocol, (relative, marker)
