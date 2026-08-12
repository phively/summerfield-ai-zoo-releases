#!/usr/bin/env python3
"""Structural and behavioral regression tests for the meal-planner plugin."""

import json
import re
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = PLUGIN_ROOT / "skills"
SHARED_HANDOFF = PLUGIN_ROOT / "shared" / "handoff-contracts.md"
SKILL_NAMES = ("meal-planner", "personal-chef", "personal-shopper")
SHARED_LINK = "../../shared/handoff-contracts.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def skill_text(name: str) -> str:
    return read(SKILLS_ROOT / name / "SKILL.md")


def test_canonical_plugin_structure() -> None:
    manifest_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
    manifest = json.loads(read(manifest_path))

    assert manifest["name"] == PLUGIN_ROOT.name == "meal-planner"
    assert manifest["skills"] == "./skills/"
    assert manifest["version"] == "1.0.0"
    assert manifest["description"]
    assert manifest["author"]["name"]
    assert isinstance(manifest["interface"]["defaultPrompt"], list)
    assert len(manifest["interface"]["defaultPrompt"]) <= 3

    for name in SKILL_NAMES:
        root = SKILLS_ROOT / name
        assert (root / "SKILL.md").is_file()
        assert (root / "agents" / "openai.yaml").is_file()
        assert (root / "assets" / "icon.svg").is_file()


def test_all_skill_local_markdown_links_resolve() -> None:
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for name in SKILL_NAMES:
        skill_path = SKILLS_ROOT / name / "SKILL.md"
        links = link_pattern.findall(read(skill_path))
        assert links, f"{name} should link to its required resources"
        for link in links:
            if "://" not in link and not link.startswith("#"):
                assert (skill_path.parent / link).resolve().is_file(), (
                    f"Broken local resource link in {name}: {link}"
                )


def test_meal_planner_functionality_contract() -> None:
    planner = skill_text("meal-planner")
    household_profile = read(
        SKILLS_ROOT / "meal-planner" / "references" / "household-profile.md"
    )
    for requirement in (
        "Allergies and confirmed medical restrictions",
        "Run the intake checkpoint",
        "Safety approval remains with `meal-planner`",
        "checkout spending separately from allocated meal cost",
    ):
        assert requirement in planner
    assert "`Household Preferences` or a clearly equivalent title" in planner
    for tab in (
        "`Household Profile`",
        "`Safety Constraints`",
        "`Planning Preferences`",
        "`Pantry Inventory`",
    ):
        assert tab in household_profile


def test_personal_chef_functionality_contract() -> None:
    chef = skill_text("personal-chef")
    preference_records = read(
        SKILLS_ROOT / "personal-chef" / "references" / "preference-records.md"
    )
    for requirement in (
        "Own recipe work and preference memory",
        "Browse to the original or authoritative recipe page",
        "Label synthesized recipes as original",
        "Prefer Google Sheets",
    ):
        assert requirement in chef
    assert "Household Preferences" in preference_records
    assert "Recipe History" in preference_records
    assert "`Meal Preferences` or a clearly equivalent title" in chef
    assert "When creating a new workbook, use `Meal Preferences`" in preference_records


def test_personal_shopper_functionality_contract() -> None:
    shopper = skill_text("personal-shopper")
    preferences = read(
        SKILLS_ROOT / "personal-shopper" / "references" / "store-preferences.md"
    )
    pricing = read(
        SKILLS_ROOT / "personal-shopper" / "references" / "pricing-and-allocation.md"
    )
    for requirement in (
        "Require finalized recipes",
        "Subtract only confirmed pantry quantities",
        "checkout estimate based on packages purchased",
        "meal-cost estimate based on quantities consumed",
    ):
        assert requirement in shopper
    assert "Require the user's explicit consent" in preferences
    assert "shared by several meals in proportion" in pricing
    assert "`Grocery Preferences` or a clearly equivalent title" in shopper
    assert "`Store Preferences`" in preferences
    assert "`Price Tracker`" in preferences


def test_canonical_workbooks_and_tabs_are_shared_through_handoffs() -> None:
    shared = read(SHARED_HANDOFF)
    expected_workbooks = {
        "`Household Preferences`": (
            "`Household Profile`",
            "`Safety Constraints`",
            "`Planning Preferences`",
            "`Pantry Inventory`",
        ),
        "`Meal Preferences`": ("`Household Preferences`", "`Recipe History`"),
        "`Grocery Preferences`": ("`Store Preferences`", "`Price Tracker`"),
    }
    for workbook, tabs in expected_workbooks.items():
        assert workbook in shared
        for tab in tabs:
            assert tab in shared
    assert "exact workbook title and link or file identity" in shared
    assert "never create skill-local static copies" in shared


def test_shared_handoff_contract_is_accessible_without_skill_copies() -> None:
    shared = read(SHARED_HANDOFF)
    assert "Personal Chef to Meal Planner" in shared
    assert "Meal Planner to Personal Shopper" in shared
    assert "Personal Shopper to Meal Planner" in shared

    for name in SKILL_NAMES:
        skill_path = SKILLS_ROOT / name / "SKILL.md"
        assert f"]({SHARED_LINK})" in read(skill_path)
        assert (skill_path.parent / SHARED_LINK).resolve() == SHARED_HANDOFF.resolve()

    copied_contracts = list(SKILLS_ROOT.rglob("handoff-contracts.md"))
    assert copied_contracts == [], "Use the plugin-level handoff contract, not local copies"


def test_chef_planner_handoff_preserves_safety_and_recipe_fields() -> None:
    shared = read(SHARED_HANDOFF)
    planner = skill_text("meal-planner")
    chef = skill_text("personal-chef")
    for field in (
        "ingredient quantities",
        "planned servings",
        "material adaptations",
        "constraint-sensitive ingredients",
        "preference evidence",
    ):
        assert field in shared.lower()
    assert "The meal planner owns final safety approval" in shared
    assert "Do not independently redo recipe selection after a valid handoff" in planner
    assert "Return a structured handoff" in chef


def test_planner_shopper_handoff_preserves_purchase_constraints() -> None:
    shared = read(SHARED_HANDOFF)
    planner = skill_text("meal-planner")
    shopper = skill_text("personal-shopper")
    for field in (
        "confirmed pantry quantities",
        "preferred stores in effective order",
        "permitted substitutions",
        "checkout spending",
        "unpriced items",
    ):
        assert field in shared.lower()
    assert "after recipe selection and safety review are complete" in planner
    assert "Begin a valid `meal-planner` handoff without re-requesting" in shopper
