#!/usr/bin/env python3
"""Structural and behavioral contract tests for work-smarter."""

import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def test_full_validator() -> None:
    assert load_validator().main() == 0


def test_research_briefing_matches_installed_work_smarter_copy() -> None:
    source = Path("/root/.codex/plugins/cache/workspace-directory/work-smarter/1.1.1/skills/research-briefing")
    bundled = ROOT / "skills" / "research-briefing"
    if source.is_dir():
        source_files = sorted(path.relative_to(source) for path in source.rglob("*") if path.is_file())
        bundled_files = sorted(path.relative_to(bundled) for path in bundled.rglob("*") if path.is_file())
        assert source_files == bundled_files
        for relative in source_files:
            assert (source / relative).read_bytes() == (bundled / relative).read_bytes()


def test_research_checkpoint_is_preserved() -> None:
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")
    assert "Begin with a research-scope checkpoint" in research
    assert "Ask the user to confirm or revise this scope, then wait" in research
    assert "must not treat initiation of the handoff as confirmation" in contract


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

    for skill in ("remember-me", "research-briefing", "superb-skills", "teach-me"):
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
        "meal-planner:personal-chef", "meal-planner:personal-shopper",
    ):
        assert owner in records
    for filename in (
        "communication-collaboration.md", "values-goals.md",
        "lifestyle-routines.md", "entertainment-interests.md",
        "travel-places.md", "household-relationships.md", "technology-tools.md",
    ):
        assert filename in records


def test_bundled_skills_consult_remember_me_selectively() -> None:
    for skill_name in ("research-briefing", "superb-skills"):
        skill = read(ROOT / "skills" / skill_name / "SKILL.md")
        assert "remember-me/index.md" in skill
        assert "smallest sufficient set of relevant current context" in skill
        assert "Expand retrieval when the bounded context" in skill
        assert "silently changing durable memory" in skill
    teaching = read(ROOT / "skills" / "teach-me" / "SKILL.md")
    assert "smallest sufficient set of relevant current context" in teaching
    assert "silently changing durable memory" in teaching
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    assert "it is not evidence for an external claim" in research


def test_remember_me_contracts_preserve_authority_and_confirmation() -> None:
    contract = read(ROOT / "shared" / "handoff-contracts.md")
    for heading in (
        "Teach Me to Research Briefing",
        "Bundled Skills to Remember Me: targeted consultation",
        "Bundled Skills to Remember Me: durable update request",
        "Remember Me to External Domain Owner",
    ):
        assert heading in contract
    assert "The Remember Me summary is a cache and pointer only" in contract
    assert "Other bundled skills must not maintain competing personal-profile files" in contract
    assert "Require confirmation before persisting an inference" in contract


def test_manifest_represents_all_bundled_skills() -> None:
    manifest = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))
    description = manifest["description"]
    assert "research" in description
    assert "interactive teaching" in description
    assert "instruction design" in description
    assert "personal-context indexing" in description


def test_superb_skills_uses_conditional_memory() -> None:
    skill = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    reference = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    assert "Do not create persistent working-memory files by default" in skill
    assert "Use one current-state file" in skill
    assert "Do not read it when the gate fails" in skill
    assert "Designate exactly one source as authoritative" in reference
    assert "Read the working briefing first" in reference


def test_memory_guidance_prioritizes_recall_then_tokens_then_speed() -> None:
    superb = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    memory = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")

    priorities = (
        "1. Preserve reliable recall",
        "2. Minimize the tokens",
        "3. Minimize the time",
    )
    positions = [memory.index(priority) for priority in priorities]
    assert positions == sorted(positions)
    assert "Never improve a lower-ranked objective by weakening a higher-ranked one" in memory
    assert "Never trade a higher-ranked objective for a lower-ranked one" in superb
    assert "Reliable recall takes priority over reducing context tokens" in remember

    for artifact in (superb, memory, remember, records, contract):
        assert "incomplete" in artifact
        assert "stale" in artifact
        assert "ambiguous" in artifact
        assert "conflicting" in artifact
        assert "consequential detail" in artifact

    assert "Keep the transaction narrow only when" in records
    assert "Expand beyond the index summary" in contract


def test_memory_maintenance_triggers_are_measurable_and_non_destructive() -> None:
    superb = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    memory = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    assert "measurable lifecycle-review trigger" in superb
    for phrase in ("8 KiB", "16 KiB", "180 days", "conservative default design heuristic"):
        assert phrase in memory
        assert phrase in records
    assert "Any trigger can make an audit due. No trigger decides" in memory
    assert "A due trigger requires review, not automatic" in remember


def test_comparative_claims_require_basis_but_preserve_labeled_opinion() -> None:
    superb = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    instruction = read(ROOT / "skills" / "superb-skills" / "references" / "instruction-design.md")
    evaluation = read(ROOT / "skills" / "superb-skills" / "references" / "evaluation.md")
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")

    for artifact in (superb, instruction, research, remember):
        assert "explicit or implicit comparison" in artifact
        assert "comparison set" in artifact or "reference set" in artifact
        assert "supported absolute property" in artifact
        assert "subjective" in artifact
    assert "unsupported explicit and implicit comparisons" in evaluation
    assert "reference set and supporting evidence" in contract


def test_record_identity_prefers_provider_ids_and_permalinks() -> None:
    memory = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")

    for artifact in (memory, remember, records, contract):
        assert "provider" in artifact
        assert "library or container" in artifact
        assert "permalink" in artifact
        assert "fallback" in artifact
    assert "Treat a copy as a new identity" in records
    assert "never choose among same-named candidates by filename alone" in memory


def test_memory_review_uses_independent_trigger_classes() -> None:
    memory = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")

    for artifact in (memory, records):
        for phrase in (
            "25 material changes", "25 percent", "conflict", "pointer",
            "bounded retrieval", "substantial unrelated content",
        ):
            assert phrase in artifact
    assert "No trigger decides the lifecycle action by itself" in memory
    assert "table of contents or section map is a conditional retrieval aid" in records


def test_context_compaction_is_distinct_from_record_compaction() -> None:
    superb = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    memory = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")

    assert "Conversation-context compaction does not by itself" in superb
    assert "Conversation-context compaction is different from persistent-record compaction" in memory
    assert "Conversation-context compaction is not persistent-record compaction" in records
    for artifact in (superb, memory, records):
        assert "recheck exact" in artifact


def test_memory_audit_validates_complete_staged_rewrite_and_rejects_loss() -> None:
    audit = load_memory_audit_validator()
    with TemporaryDirectory() as directory:
        root = Path(directory)
        before = root / "before"
        after = root / "after"
        invalid = root / "invalid"
        broken = root / "broken"
        before.mkdir()
        after.mkdir()
        invalid.mkdir()
        broken.mkdir()
        original = (
            "# Index\n\n- Record ID: PREF-001\n- Limit: $5,000\n- Source: user interview\n"
            "- Prefers concise updates.\n- History: RMH-2026-01-01-01\n- duplicate wording\n"
        )
        history = "# History\n\n## RMH-2026-01-01-01\n\n- Prior preference: detailed updates.\n"
        (before / "index.md").write_text(original, encoding="utf-8")
        (before / "history.md").write_text(history, encoding="utf-8")
        compact_index = (
            "# Index\n\n- Record ID: PREF-001\n- Prefers concise status updates.\n"
            "- History: RMH-2026-01-01-01\n"
        )
        (after / "index.md").write_text(compact_index, encoding="utf-8")
        (after / "topic.md").write_text("# Topic\n\n- Limit: $5,000\n- Source: user interview\n", encoding="utf-8")
        (after / "history.md").write_text(history, encoding="utf-8")
        (invalid / "index.md").write_text(compact_index, encoding="utf-8")
        (invalid / "topic.md").write_text("# Topic\n\n- Source: user interview\n", encoding="utf-8")
        (invalid / "history.md").write_text(history, encoding="utf-8")
        (broken / "index.md").write_text(compact_index, encoding="utf-8")
        (broken / "topic.md").write_text("# Topic\n\n- Limit: $5,000\n- Source: user interview\n", encoding="utf-8")
        (broken / "history.md").write_text("# History\n\n- Prior preference: detailed updates.\n", encoding="utf-8")

        before_items = [
            {"id": "limit", "kind": "numeric_rule", "path": "index.md", "text": "- Limit: $5,000"},
            {"id": "source", "kind": "provenance", "path": "index.md", "text": "- Source: user interview"},
            {"id": "record-id", "kind": "stable_id", "path": "index.md", "text": "- Record ID: PREF-001"},
            {"id": "history-pointer", "kind": "pointer", "path": "index.md", "text": "- History: RMH-2026-01-01-01",
             "target_path": "history.md", "target_text": "## RMH-2026-01-01-01"},
            {"id": "history-item", "kind": "historical_item", "path": "history.md", "text": "- Prior preference: detailed updates."},
            {"id": "preference", "kind": "active_fact", "path": "index.md", "text": "- Prefers concise updates."},
            {"id": "duplicate", "kind": "valueless_duplicate", "path": "index.md", "text": "- duplicate wording"},
        ]
        after_items = [
            {"id": "limit-after", "kind": "numeric_rule", "path": "topic.md", "text": "- Limit: $5,000"},
            {"id": "source-after", "kind": "provenance", "path": "topic.md", "text": "- Source: user interview"},
            {"id": "record-id-after", "kind": "stable_id", "path": "index.md", "text": "- Record ID: PREF-001"},
            {"id": "history-pointer-after", "kind": "pointer", "path": "index.md", "text": "- History: RMH-2026-01-01-01",
             "target_path": "history.md", "target_text": "## RMH-2026-01-01-01"},
            {"id": "history-item-after", "kind": "historical_item", "path": "history.md", "text": "- Prior preference: detailed updates."},
            {"id": "preference-after", "kind": "active_fact", "path": "index.md", "text": "- Prefers concise status updates."},
        ]
        decisions = [
            {"before_id": "limit", "disposition": "moved", "after_ids": ["limit-after"]},
            {"before_id": "source", "disposition": "moved", "after_ids": ["source-after"]},
            {"before_id": "record-id", "disposition": "retained", "after_ids": ["record-id-after"]},
            {"before_id": "history-pointer", "disposition": "retained", "after_ids": ["history-pointer-after"]},
            {"before_id": "history-item", "disposition": "retained", "after_ids": ["history-item-after"]},
            {"before_id": "preference", "disposition": "reworded", "after_ids": ["preference-after"],
             "semantic_review": "passed", "justification": "Equivalent concise wording"},
            {"before_id": "duplicate", "disposition": "removed", "after_ids": [],
             "justification": "Valueless duplicate"},
        ]
        ledger = {
            "schema_version": 1,
            "before_files": audit.markdown_inventory(before),
            "after_files": audit.markdown_inventory(after),
            "before_items": before_items,
            "after_items": after_items,
            "decisions": decisions,
            "new_after_ids": [],
        }
        audit.validate_audit(before, after, ledger)

        invalid_ledger = dict(ledger)
        invalid_ledger["after_files"] = audit.markdown_inventory(invalid)
        invalid_ledger["after_items"] = [item for item in after_items if item["id"] != "limit-after"]
        failed = False
        try:
            audit.validate_audit(before, invalid, invalid_ledger)
        except audit.AuditError:
            failed = True
        assert failed
        assert (before / "index.md").read_text(encoding="utf-8") == original

        broken_ledger = dict(ledger)
        broken_ledger["after_files"] = audit.markdown_inventory(broken)
        pointer_failed = False
        try:
            audit.validate_audit(before, broken, broken_ledger)
        except audit.AuditError:
            pointer_failed = True
        assert pointer_failed
        assert (before / "history.md").read_text(encoding="utf-8") == history


def test_contract_is_single_and_explicit() -> None:
    contracts = list(ROOT.rglob("handoff-contracts.md"))
    assert contracts == [ROOT / "shared" / "handoff-contracts.md"]
    skill = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    assert "../../shared/handoff-contracts.md" in skill


def test_superb_skills_routes_conditional_references() -> None:
    root = ROOT / "skills" / "superb-skills"
    skill = read(root / "SKILL.md")
    expected = {
        "instruction-design.md": "one-time prompts",
        "plugin-architecture.md": "multiple coordinated skills",
        "evaluation.md": "comparing architectures",
        "working-memory.md": "working-memory gate",
    }
    for filename, trigger in expected.items():
        assert (root / "references" / filename).is_file()
        assert f"](references/{filename})" in skill
        assert trigger in skill
    assert "load no reference merely because it exists" in skill


def test_skill_creator_remains_implementation_authority() -> None:
    skill = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    plugin = read(ROOT / "skills" / "superb-skills" / "references" / "plugin-architecture.md")
    assert "Invoke `skill-creator`" in skill
    assert "Do not duplicate its platform-specific implementation procedure" in skill
    assert "Treat it as authoritative" in plugin


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
    assert "`superb-skills`, `research-briefing`, or `teach-me`" in contract


def test_teach_me_standalone_mirrors_references_without_plugin_dependencies() -> None:
    plugin_root = ROOT / "skills" / "teach-me"
    standalone_root = ROOT.parents[1] / "skills" / "teach-me"
    plugin = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))

    for relative in (
        Path("references/teaching-workflow.md"),
        Path("references/personalities/nicer-socrates.md"),
        Path("assets/icon-small.svg"),
        Path("assets/icon-large.svg"),
    ):
        assert read(plugin_root / relative) == read(standalone_root / relative)

    standalone_skill = read(standalone_root / "SKILL.md")
    standalone_agent = read(standalone_root / "agents" / "openai.yaml")
    assert "Standalone teaching skill" in standalone_skill
    assert f'metadata:\n  version: "{plugin["version"]}"\n---' in standalone_skill
    assert "Ask the user to confirm or revise the scope, then wait" in standalone_skill
    for forbidden in ("work-smarter", "remember-me", "research-briefing", "handoff-contracts"):
        assert forbidden not in standalone_skill
        assert forbidden not in standalone_agent
    assert "dependencies:" not in standalone_agent


def test_eval_suite_covers_required_behaviors() -> None:
    cases = json.loads(read(ROOT / "evals" / "regression.json"))["cases"]
    ids = {case["id"] for case in cases}
    assert {
        "route-superb-skills", "negative-route", "research-handoff",
        "research-nontrigger", "research-confirmation", "memory-no-file",
        "memory-single-file", "memory-split", "memory-conflict",
        "memory-missing", "memory-recall-before-token-reduction",
        "memory-token-reduction-before-speed", "memory-narrow-update-fallback",
        "memory-maintenance-trigger", "memory-audit-success",
        "memory-audit-loss-failure", "research-opening-influential-sources",
        "research-large-request-phase-choice",
        "research-ordinary-request-no-phase-warning",
        "research-phase-choice-default-continuous",
        "research-phase-checkpoint-no-response",
        "research-phased-work-stops-after-log",
        "research-waiver-no-phase-pause",
        "research-unsupported-implicit-comparison",
        "research-supported-comparison", "research-subjective-comparison",
        "memory-nonsize-audit-trigger", "memory-context-vs-record-compaction",
        "memory-conditional-toc", "memory-provider-identity-pointer",
        "contract-failure", "backward-compatibility",
        "remember-explicit", "remember-indirect-query", "remember-negative",
        "remember-owned-topic", "remember-external-career",
        "remember-targeted-consultation", "remember-missing-source",
        "remember-stale-summary", "remember-source-conflict",
        "remember-duplicate-index", "remember-task-override",
        "remember-history-gate", "remember-sensitive-content",
        "teach-explicit", "teach-indirect", "teach-negative-direct-answer",
        "teach-research-first", "teach-research-failure",
        "teach-default-personality", "teach-selected-personality",
        "teach-stuck-explanation", "teach-premise-challenge",
        "teach-memory-consultation", "teach-memory-no-session-write",
    }.issubset(ids)


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
