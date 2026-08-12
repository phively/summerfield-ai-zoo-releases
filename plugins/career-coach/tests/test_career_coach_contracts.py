#!/usr/bin/env python3
"""Structural and behavioral regression tests for the career-coach plugin."""

import json
import re
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = PLUGIN_ROOT / "skills"
SHARED_HANDOFF = PLUGIN_ROOT / "shared" / "handoff-contracts.md"
SKILL_NAMES = ("career-direction", "evaluate-opportunity", "update-resume")
SHARED_LINK = "../../shared/handoff-contracts.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def skill_text(name: str) -> str:
    return read(SKILLS_ROOT / name / "SKILL.md")


def test_canonical_plugin_and_skill_structure() -> None:
    manifest = json.loads(read(PLUGIN_ROOT / ".codex-plugin" / "plugin.json"))
    assert manifest["name"] == PLUGIN_ROOT.name == "career-coach"
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
        assert "`career-coach-preferences.md` or a clearly equivalent" in skill
        assert f"]({SHARED_LINK})" in skill


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
    assert "Update the selected file in place" in direction
    assert "Do not create a skill-local copy" in direction
    assert "discovery-framework.md" in direction
    assert "decision-criteria.md" in direction
    assert "Canonical record structure" in criteria
    assert not list(PLUGIN_ROOT.rglob("career_direction_record.md"))
    assert not list(PLUGIN_ROOT.rglob("career-coach-preferences.md"))


def test_consumer_skills_search_record_without_owning_copies() -> None:
    for name in ("evaluate-opportunity", "update-resume"):
        skill = skill_text(name)
        assert "Search the selected career direction record" in skill
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
    assert "exact career direction record identity" in shared
    assert "cannot establish an unverified resume claim" in shared
    assert "Never create skill-local static copies" in shared


def test_regression_suite_covers_shared_record_behaviors() -> None:
    suite = json.loads(read(PLUGIN_ROOT / "evals" / "regression.json"))
    case_ids = {case["id"] for case in suite["cases"]}
    assert {
        "shared-direction-record",
        "direction-update-handoff",
        "preference-file-conflict",
    }.issubset(case_ids)
