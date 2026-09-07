#!/usr/bin/env python3
"""Structural and behavioral regression tests for the meal-planner plugin."""

from copy import deepcopy
import importlib.util
import json
import re
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = PLUGIN_ROOT / "skills"
SHARED_HANDOFF = PLUGIN_ROOT / "shared" / "handoff-contracts.md"
RECORD_MANAGEMENT = PLUGIN_ROOT / "shared" / "record-management.md"
WORKBOOK_AUDIT_SCHEMA = PLUGIN_ROOT / "shared" / "workbook-audit-schema.md"
SKILL_NAMES = ("meal-planner", "personal-chef", "personal-shopper")
SHARED_LINK = "../../shared/handoff-contracts.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def skill_text(name: str) -> str:
    return read(SKILLS_ROOT / name / "SKILL.md")


def load_workbook_audit_validator():
    path = PLUGIN_ROOT / "scripts" / "validate_workbook_audit.py"
    spec = importlib.util.spec_from_file_location("validate_workbook_audit", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_canonical_plugin_structure() -> None:
    manifest_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
    manifest = json.loads(read(manifest_path))

    assert manifest["name"] == PLUGIN_ROOT.name == "meal-planner"
    assert manifest["version"].split("+", 1)[0] == "1.3.0"
    assert manifest["skills"] == "./skills/"
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:\+codex\.[0-9A-Za-z.-]+)?", manifest["version"])
    assert manifest["description"]
    assert manifest["author"]["name"]
    assert isinstance(manifest["interface"]["defaultPrompt"], list)
    assert len(manifest["interface"]["defaultPrompt"]) <= 3

    for name in SKILL_NAMES:
        root = SKILLS_ROOT / name
        assert (root / "SKILL.md").is_file()
        assert (root / "agents" / "openai.yaml").is_file()
        assert (root / "assets" / "icon-small.svg").is_file()
        assert (root / "assets" / "icon-large.svg").is_file()


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
    assert "load the saved order from `Store Preferences`" in shopper
    assert "load the saved order from the grocery price tracker" not in shopper


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
    assert "stable key column and record ID" in shared
    assert "A workbook title, worksheet title, or row number alone is insufficient" in shared


def test_workbook_native_routing_and_format_aware_triggers() -> None:
    detail = read(RECORD_MANAGEMENT)
    schema = read(WORKBOOK_AUDIT_SCHEMA)
    for phrase in (
        "Native identities and routing",
        "`Record Index` worksheet",
        "Do not create a Markdown or other sidecar index",
        "complete relevant recall, fewer cells or tokens",
        "more than 180 days old",
        "exceeds 500 data rows",
        "exceeds 2,000 data rows",
        "at least 25 percent",
        "conservative design heuristics",
    ):
        assert phrase in detail
    for phrase in (
        "record:<worksheet>:<record-id>",
        "formula_review: passed",
        "every after item",
        "does not prove the connector exported everything",
    ):
        assert phrase in schema
    assert "[the workbook audit snapshot and ledger schema](workbook-audit-schema.md)" in detail
    for reference in (
        SKILLS_ROOT / "meal-planner" / "references" / "household-profile.md",
        SKILLS_ROOT / "personal-chef" / "references" / "preference-records.md",
        SKILLS_ROOT / "personal-shopper" / "references" / "store-preferences.md",
    ):
        text = read(reference)
        assert "Record Index" in text
        assert "Record ID" in text
        assert "row" in text.lower()


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


def test_every_skill_accesses_shared_record_contract() -> None:
    for name in SKILL_NAMES:
        skill = skill_text(name)
        assert "](../../shared/record-management.md)" in skill
    assert RECORD_MANAGEMENT.is_file()


def test_record_registry_defines_canonical_authority_and_ownership() -> None:
    detail = read(RECORD_MANAGEMENT)
    shared = read(SHARED_HANDOFF)
    for identity in (
        "`meal-plan-current.md`",
        "`meal-plan-history.md`",
        "`Household History`",
        "`Household Preferences History`",
        "`Ingredient Ratings`",
        "`Ingredient Ratings History`",
        "`Recipe Ratings`",
        "`Recipe History`",
        "`Store Preferences History`",
        "`Price Tracker`",
    ):
        assert identity in detail and identity in shared
    assert "All Meal Planner skills" in detail
    assert "only `meal-planner` creates or updates" in shared
    assert "only `personal-chef` creates or updates" in shared
    assert "only `personal-shopper` creates or updates" in shared


def test_meal_plan_lifecycle_and_failure_contract() -> None:
    detail = read(RECORD_MANAGEMENT)
    planner = skill_text("meal-planner")
    for phrase in (
        "MP-YYYY-MM-DD-NN",
        "MH-YYYY-MM-DD-NN",
        "exactly one plan is current",
        "Do not archive abandoned drafts",
        "A change requiring both current and history writes is incomplete",
        "do not claim a coherent update",
    ):
        assert phrase in detail
    assert "Finalize and maintain meal-plan records" in planner
    assert "Persist only a user-confirmed finalized plan" in planner


def test_rating_pairs_and_feedback_gate_preserve_attribution() -> None:
    detail = read(RECORD_MANAGEMENT)
    chef = skill_text("personal-chef")
    preferences = read(
        SKILLS_ROOT / "personal-chef" / "references" / "preference-records.md"
    )
    for tab in (
        "Household Preferences",
        "Household Preferences History",
        "Ingredient Ratings",
        "Ingredient Ratings History",
        "Recipe Ratings",
        "Recipe History",
    ):
        assert tab in chef and tab in preferences
    assert "A plan is not evidence that it was made" in preferences
    assert "Elapsed time alone is insufficient" in detail
    assert "Recipe-specific feedback does not establish a general ingredient preference" in detail
    assert "Individual feedback does not establish a household-wide preference" in detail
    assert "Do not silently generalize a preparation-specific ingredient rating" in detail


def test_handoffs_include_record_identity_confirmation_and_boundaries() -> None:
    shared = read(SHARED_HANDOFF)
    for heading in (
        "Meal Planner to Personal Chef",
        "Personal Chef to Meal Planner",
        "Meal Planner to Personal Shopper",
        "Personal Shopper to Meal Planner",
    ):
        assert heading in shared
    for phrase in (
        "exact current and historical identities",
        "stable entry identifier",
        "confirmation status",
        "prohibited information",
        "A newly requested plan triggers the retrospective",
    ):
        assert phrase in shared


def test_workbook_audit_completes_and_fails_closed() -> None:
    audit = load_workbook_audit_validator()
    before = {
        "schema_version": 1,
        "workbook": {"resource_id": "wb-meals-1", "title": "Meal Preferences"},
        "sheets": [
            {
                "name": "Recipe Ratings",
                "role": "current",
                "columns": [
                    {"name": "Record ID"}, {"name": "Rating"}, {"name": "Score"},
                    {"name": "History Pointer"}, {"name": "Legacy Notes", "disposable": True},
                ],
                "tables": [{"name": "RecipeRatings", "range": "A1:E2"}],
                "rows": [{
                    "record_id": "RR-1",
                    "values": {"Record ID": "RR-1", "Rating": 4, "History Pointer": "MH-1"},
                    "formulas": {"Score": "=B2*20"},
                    "validations": {"Rating": "whole-number:1-5"},
                    "references": [{"workbook_id": "wb-meals-1", "sheet": "Recipe History", "record_id": "MH-1"}],
                }],
            },
            {
                "name": "Recipe History",
                "role": "history",
                "columns": [{"name": "Record ID"}, {"name": "Prior Rating"}],
                "tables": [{"name": "RecipeHistory", "range": "A1:B2"}],
                "rows": [{
                    "record_id": "MH-1",
                    "values": {"Record ID": "MH-1", "Prior Rating": 3},
                    "formulas": {}, "validations": {}, "references": [],
                }],
            },
        ],
        "named_ranges": [{"name": "CurrentRecipeRatings", "sheet": "Recipe Ratings", "range": "A1:E2"}],
    }
    after = deepcopy(before)
    after["sheets"][0]["columns"] = [
        column for column in after["sheets"][0]["columns"] if column["name"] != "Legacy Notes"
    ]
    after["sheets"][0]["tables"][0]["range"] = "A1:D2"
    after["named_ranges"][0]["range"] = "A1:D2"
    after["sheets"].append({
        "name": "Record Index",
        "role": "index",
        "columns": [{"name": "Record ID"}, {"name": "Worksheet"}, {"name": "Stable Key Column"}],
        "tables": [{"name": "RecordIndex", "range": "A1:C2"}],
        "rows": [{
            "record_id": "IDX-1",
            "values": {"Record ID": "IDX-1", "Worksheet": "Recipe Ratings", "Stable Key Column": "Record ID"},
            "formulas": {}, "validations": {},
            "references": [{"workbook_id": "wb-meals-1", "sheet": "Recipe Ratings", "record_id": "RR-1"}],
        }],
    })

    before_items = audit.inventory(before)
    after_items = audit.inventory(after)
    decisions = []
    for ref, item in before_items.items():
        if ref == "column:Recipe Ratings:Legacy Notes":
            decisions.append({"before_ref": ref, "disposition": "removed", "after_refs": [],
                              "justification": "Unused disposable column"})
        elif ref in {"table:Recipe Ratings:RecipeRatings", "named-range:CurrentRecipeRatings"}:
            decisions.append({"before_ref": ref, "disposition": "updated", "after_refs": [ref],
                              "authorized": True, "justification": "Range contracted after disposable column removal"})
        else:
            assert ref in after_items
            decisions.append({"before_ref": ref, "disposition": "retained", "after_refs": [ref]})
    new_refs = sorted(set(after_items) - set(before_items))
    ledger = {
        "schema_version": 1,
        "before_hash": audit.canonical_hash(before),
        "after_hash": audit.canonical_hash(after),
        "decisions": decisions,
        "new_after_refs": new_refs,
        "new_items_justification": "Authorized workbook-local routing index",
    }
    before_hash = audit.canonical_hash(before)
    audit.validate_audit(before, after, ledger)

    invalid_snapshots = []
    omitted = deepcopy(after)
    omitted["sheets"][0]["rows"] = []
    omitted["sheets"][2]["rows"][0]["references"] = []
    invalid_snapshots.append(omitted)
    changed_formula = deepcopy(after)
    changed_formula["sheets"][0]["rows"][0]["formulas"]["Score"] = "=B2*10"
    invalid_snapshots.append(changed_formula)
    changed_validation = deepcopy(after)
    changed_validation["sheets"][0]["rows"][0]["validations"]["Rating"] = "whole-number:1-10"
    invalid_snapshots.append(changed_validation)
    duplicate_key = deepcopy(after)
    duplicate_key["sheets"][0]["rows"].append(deepcopy(duplicate_key["sheets"][0]["rows"][0]))
    invalid_snapshots.append(duplicate_key)
    broken_reference = deepcopy(after)
    broken_reference["sheets"][0]["rows"][0]["references"][0]["record_id"] = "MH-MISSING"
    invalid_snapshots.append(broken_reference)
    broken_named_range = deepcopy(after)
    broken_named_range["named_ranges"][0]["sheet"] = "Missing Sheet"
    invalid_snapshots.append(broken_named_range)

    for invalid in invalid_snapshots:
        failed = False
        invalid_ledger = dict(ledger)
        invalid_ledger["after_hash"] = audit.canonical_hash(invalid)
        try:
            audit.validate_audit(before, invalid, invalid_ledger)
        except audit.AuditError:
            failed = True
        assert failed
        assert audit.canonical_hash(before) == before_hash


def test_record_management_eval_has_required_cases() -> None:
    suite = json.loads(read(PLUGIN_ROOT / "evals" / "record-management.json"))
    cases = {case["id"]: case for case in suite["cases"]}
    assert {
        "finalize-first-plan",
        "replace-current-plan",
        "unmade-recipe-no-rating",
        "initial-recipe-rating",
        "material-rating-revision",
        "elapsed-time-alone",
        "recipe-specific-not-general",
        "ingredient-rating-preparation-context",
        "shopper-current-plan-only",
        "duplicate-record-authority",
        "partial-rating-write",
        "native-workbook-index",
        "workbook-audit-trigger",
        "workbook-audit-success",
        "workbook-audit-loss",
        "workbook-audit-structural-failure",
    } <= set(cases)
    for case in cases.values():
        assert case["expected_files_read"]
        assert isinstance(case["forbidden_files_read"], list)
        assert case["authoritative_result"]
        assert isinstance(case["permitted_writes"], list)
        assert case["failure_criteria"]
