import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import yaml


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = PLUGIN_ROOT / "skills" / "personal-shopper"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_manifest_and_skill_metadata_are_installable() -> None:
    manifest = json.loads(read(PLUGIN_ROOT / ".codex-plugin" / "plugin.json"))
    assert manifest["name"] == "personal-shopper"
    assert manifest["version"] == "1.1.0"
    assert manifest["skills"] == "./skills/"
    assert manifest["interface"]["displayName"] == "Personal Shopper"
    assert "Meal Planner's approved grocery-handoff/v1 packet" in manifest["interface"]["defaultPrompt"][1]
    assert "Meal Planner's approved grocery-handoff/v1 packet" in read(
        SKILL_ROOT / "agents" / "openai.yaml"
    )

    for icon in (manifest["interface"]["composerIcon"], manifest["interface"]["logo"]):
        assert (PLUGIN_ROOT / icon).is_file()

    skill = SKILL_ROOT / "SKILL.md"
    metadata = SKILL_ROOT / "agents" / "openai.yaml"
    assert skill.is_file()
    fields = yaml.safe_load(read(skill).split("---", 2)[1])
    assert fields["name"] == "personal-shopper"

    interface = yaml.safe_load(read(metadata))["interface"]
    for key in ("icon_small", "icon_large"):
        assert (SKILL_ROOT / interface[key]).is_file()


def test_package_copy_resolves_all_local_resources_without_sibling_plugins(tmp_path: Path) -> None:
    installed = tmp_path / "personal-shopper"
    shutil.copytree(PLUGIN_ROOT, installed)
    manifest = json.loads(read(installed / ".codex-plugin" / "plugin.json"))
    for icon in (manifest["interface"]["composerIcon"], manifest["interface"]["logo"]):
        target = (installed / icon).resolve()
        assert target.is_relative_to(installed.resolve()) and target.is_file()

    skill_root = installed / "skills" / "personal-shopper"
    metadata = yaml.safe_load(read(skill_root / "agents" / "openai.yaml"))["interface"]
    for key in ("icon_small", "icon_large"):
        target = (skill_root / metadata[key]).resolve()
        assert target.is_relative_to(installed.resolve()) and target.is_file()

    validator = installed / "scripts" / "validate_workbook_audit.py"
    assert validator.is_file()
    validator_help = subprocess.run(
        [sys.executable, str(validator), "--help"], capture_output=True, text=True, check=False
    )
    assert validator_help.returncode == 0
    assert "before_snapshot" in validator_help.stdout

    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

    for markdown in installed.rglob("*.md"):
        for link in link_pattern.findall(read(markdown)):
            if "://" in link or link.startswith("#"):
                continue
            target_text = link.split("#", 1)[0]
            if not target_text:
                continue
            target = (markdown.parent / target_text).resolve()
            assert target.is_relative_to(installed.resolve()), (
                f"Resource escapes installed Personal Shopper package: {markdown}: {link}"
            )
            assert target.is_file(), f"Missing installed resource: {markdown}: {link}"


def test_grocery_workflow_and_identity_contract_survive_extraction() -> None:
    skill = read(SKILL_ROOT / "SKILL.md")
    grocery = read(SKILL_ROOT / "references" / "grocery-workflow.md")
    preferences = read(SKILL_ROOT / "references" / "store-preferences.md")
    pricing = read(SKILL_ROOT / "references" / "pricing-and-allocation.md")
    handoff = read(PLUGIN_ROOT / "shared" / "handoff-contracts.md")
    records = read(PLUGIN_ROOT / "shared" / "record-management.md")

    for phrase in (
        "finalized, safety-reviewed recipes",
        "Subtract only confirmed pantry quantities",
        "package counts",
        "Purchase quantity",
        "Checkout cost",
        "Allocated meal cost",
    ):
        assert phrase in grocery
    assert "Direct product shopping does not require Meal Planner or recipes" in skill
    assert "Require the user's explicit consent" in preferences
    assert "shared by several meals in proportion" in pricing
    for field in (
        "Recipe IDs",
        "approved versions",
        "meal-plan identity",
        "`Grocery Preferences` workbook identity",
        "consented to persist",
        "unresolved",
    ):
        assert field.lower() in handoff.lower()

    assert "Do not create or update meal-plan, household, recipe, or rating records directly" in skill
    assert "`personal-shopper` only" in records
    assert "Household Preferences" not in records
    assert "Recipe Catalog" not in records
    assert "Do not create a Markdown or text database" in records


def test_direct_product_shopping_and_delegated_grocery_contracts_are_distinct() -> None:
    skill = read(SKILL_ROOT / "SKILL.md")
    product = read(SKILL_ROOT / "references" / "product-selection.md")
    grocery = read(SKILL_ROOT / "references" / "grocery-workflow.md")
    stores = read(SKILL_ROOT / "references" / "store-preferences.md")

    assert "direct product" in skill.lower()
    assert "delegated meal-plan grocery" in skill.lower()
    assert skill.index("direct product") < skill.index("delegated meal-plan grocery")
    assert "finalized, safety-reviewed recipes" in grocery.lower()
    assert "require finalized recipes" not in product.lower()
    assert "no recipe or meal planner prerequisite" in product.lower()
    assert "groceries" in stores.lower()
    assert "clothing" in stores.lower()


def test_service_route_and_related_alternatives_are_package_local() -> None:
    skill = read(SKILL_ROOT / "SKILL.md")
    product = read(SKILL_ROOT / "references" / "product-selection.md")
    service = read(SKILL_ROOT / "references" / "service-selection.md")
    assert "references/service-selection.md" in skill
    for text in (product, service):
        assert "alternatives" in text.lower()
        assert "restrict" in text.lower()
    assert "privacy" in service and "transparency" in service
    assert "No recipe" in service


def test_hardware_research_requires_variant_acquisition_and_usable_unit_cost() -> None:
    product = read(SKILL_ROOT / "references" / "product-selection.md")
    pricing = read(SKILL_ROOT / "references" / "pricing-and-allocation.md")
    assert "Retrieve" in product and "exact variant" in product
    for field in ("thread pitch", "coating", "strength", "pack quantity"):
        assert field in product
    assert "manufacturer access fails" in product
    assert "usable matching" in pricing


def test_front_fender_measurements_cover_crown_and_each_specified_fork_point() -> None:
    product = read(SKILL_ROOT / "references" / "product-selection.md")
    assert "smallest gap from the tire top to the underside of the fork crown" in product
    assert "intended riding pressure" in product
    assert "in addition to each manufacturer-specified fork-leg point" in product
    assert "minimum only to the points it covers" in product


def test_contractors_keep_qualification_scope_and_unpriced_exclusions_visible() -> None:
    service = read(SKILL_ROOT / "references" / "service-selection.md")
    pricing = read(SKILL_ROOT / "references" / "pricing-and-allocation.md")
    records = read(SKILL_ROOT / "references" / "shopping-records.md")
    assert "official registry" in service
    assert "insurance" in service and "unverified" in service
    assert "exclusions" in service and "disposal" in pricing
    assert "one-time" in pricing and "recurring" in pricing
    assert "service-category" in records


def test_project_route_keeps_official_fees_and_empirical_forecasts_separate() -> None:
    skill = read(SKILL_ROOT / "SKILL.md")
    service = read(SKILL_ROOT / "references" / "service-selection.md")
    project = read(SKILL_ROOT / "references" / "project-costs.md")
    assert "references/project-costs.md" in skill
    assert "project-costs.md" in service
    for term in ("official", "jurisdiction", "valuation", "nearest-rank", "ceiling", "original", "inadequate", "contingency"):
        assert term in project
    assert "ordinary estimate" in project


def test_new_plan_handoff_has_explicit_proposed_identity_without_weakening_existing_identity():
    skill_contract = read(SKILL_ROOT / "references" / "contracts" / "handoff-contracts.md")
    shared_contract = read(PLUGIN_ROOT / "shared" / "handoff-contracts.md")
    grocery = read(SKILL_ROOT / "references" / "grocery-workflow.md")
    assert skill_contract == shared_contract
    for text in (skill_contract, grocery):
        assert "identity_status: persisted" in text
        assert "identity_status: proposed" in text
        assert "native_resource: not-yet-created" in text
        assert "collision-checked" in text
        assert "existing plan" in text
    assert "Echo a proposed plan as proposed" in skill_contract


def test_recipe_list_entry_points_route_through_meal_planner():
    manifest = json.loads(read(PLUGIN_ROOT / ".codex-plugin" / "plugin.json"))
    readme = read(PLUGIN_ROOT / "README.md")
    assert "Meal Planner's approved `grocery-handoff/v1` packet" in readme
    assert "A direct product-shopping request does not require recipes or Meal Planner" in readme
    assert "finalized recipes" not in manifest["interface"]["defaultPrompt"][1]


def test_shopping_fixture_cases_have_deterministic_expected_results() -> None:
    fixture_path = PLUGIN_ROOT / "evals" / "shopping" / "fixtures.json"
    fixtures = json.loads(read(fixture_path))

    assert fixtures["evidence_limit"] == (
        "Fixtures describe expected activated-skill behavior; fixture text and static checks "
        "do not prove runtime behavior."
    )
    cases = {case["id"]: case for case in fixtures["cases"]}
    assert {"AE1", "AE2", "AE3", "AE4", "AE5"} <= cases.keys()

    grocery = cases["AE5"]["expected"]
    assert grocery["consolidated_ingredient"] == {
        "name": "canned diced tomatoes",
        "required_g": 650,
        "confirmed_pantry_g": 200,
        "purchase_g": 450,
        "package_g": 500,
        "packages": 1,
        "surplus_g": 50,
        "checkout_price": None,
    }
    assert grocery["separate_ingredients"] == [
        "certified gluten-free rolled oats",
        "standard rolled oats",
    ]
    assert grocery["unknown_prices"] == ["canned diced tomatoes"]

    cases = {case["id"]: case for case in fixtures["cases"]}
    for case_id in ("AE5", "U4-meal-planner-handoff", "AE6", "AE7"):
        packet = cases[case_id]["context"].get("recipe_packet")
        identity = packet["meal_plan_identity"]
        assert re.fullmatch(r"MP-\d{4}-\d{2}-\d{2}-\d{2}", identity["plan_id"])
        assert identity["identity_status"] == "persisted"
        assert identity["native_resource"]["provider"] == "synthetic-fixture"
        assert identity["native_resource"]["resource_id"]
        assert identity["native_resource"]["title"]
        assert identity["native_resource"]["section"]


def test_shopping_record_contract_preserves_legacy_roles_and_scoped_layouts() -> None:
    records = read(SKILL_ROOT / "references" / "shopping-records.md")
    management = read(PLUGIN_ROOT / "shared" / "record-management.md")
    formatting = read(PLUGIN_ROOT / "shared" / "artifact-formatting.md")
    cleanup = read(PLUGIN_ROOT / "shared" / "cleanup-migration.md")
    stores = read(SKILL_ROOT / "references" / "store-preferences.md")

    for role in (
        "Shopping Rules",
        "Store Preferences",
        "Owned Equipment",
        "Discount Eligibility",
        "Price Tracker",
        "Shopping History",
    ):
        assert role in records
    assert "scope (`general` or category)" in records
    assert "hard constraint" in records
    assert "missing scope or category in that legacy table means groceries" in records
    assert "Price History" in records and "Change History" in records
    assert "Record Index" in management
    assert "actual headers" in management
    assert "key column is not assumed to be column A" in records
    assert "A missing lookup does not prove that the authority" in management
    assert "separately for the requested operation" in formatting
    assert "Excel text export is not native workbook editing" in formatting
    assert "incomplete before or after snapshot cannot authorize cleanup" in cleanup
    assert "five-column" in stores


def test_u3_fixtures_cover_record_resolution_and_truthful_write_recovery() -> None:
    fixtures = json.loads(read(PLUGIN_ROOT / "evals" / "shopping" / "fixtures.json"))
    cases = {case["id"]: case for case in fixtures["cases"]}
    expected_ids = {
        "U3-legacy-role-mapping",
        "U3-scoped-records",
        "U3-read-only-route",
        "U3-current-saved-history-incomplete",
        "U3-uncertain-append",
        "U3-narrow-update-audit",
    }
    assert expected_ids <= cases.keys()

    legacy = cases["U3-legacy-role-mapping"]["expected"]
    assert legacy["resolved_roles"] == ["price evidence", "shopper preferences", "change history"]
    assert legacy["preserve_existing_schema_and_identity"] is True
    assert legacy["create_duplicate_authority"] is False

    scoped = cases["U3-scoped-records"]["expected"]
    assert scoped["authorized_scoped_records_saved"] is True
    assert scoped["task_only_correction_saved"] is False
    assert scoped["unrelated_categories_preserved"] is True

    readonly = cases["U3-read-only-route"]["expected"]
    assert readonly["useful_task_result"] is True
    assert readonly["proposed_changes_saved"] is False
    assert readonly["new_authority_created"] is False

    incomplete = cases["U3-current-saved-history-incomplete"]["expected"]
    assert incomplete["current_row"] == "verified"
    assert incomplete["required_history"] == "unverified"
    assert incomplete["combined_change"] == "incomplete"

    append = cases["U3-uncertain-append"]["expected"]
    assert append["existing_stable_key_found_before_retry"] is True
    assert append["duplicate_append"] is False

    audit = cases["U3-narrow-update-audit"]["expected"]
    assert audit["adjacent_native_properties_preserved"] is True
    assert audit["partial_snapshot_authorizes_cleanup"] is False
