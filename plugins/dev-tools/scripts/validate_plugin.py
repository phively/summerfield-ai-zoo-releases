#!/usr/bin/env python3
"""Validate the standalone dev-tools plugin package and local resource links."""

import json
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read(path: Path) -> str:
    require(path.is_file(), f"Missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def validate_manifest() -> None:
    manifest = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))
    require(manifest.get("name") == "dev-tools", "Unexpected plugin name")
    require(manifest.get("skills") == "./skills/", "Unsupported skills path")
    for field in ("version", "description", "author", "interface"):
        require(manifest.get(field), f"Missing manifest field: {field}")
    interface = manifest["interface"]
    for field in ("displayName", "shortDescription", "longDescription", "developerName", "category", "capabilities", "brandColor", "composerIcon", "logo", "defaultPrompt"):
        require(interface.get(field), f"Missing interface field: {field}")
    for field in ("composerIcon", "logo"):
        path = ROOT / interface[field].removeprefix("./")
        require(path.is_file(), f"Missing interface asset: {interface[field]}")


def parse_frontmatter(text: str, skill_name: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    require(match is not None, f"Invalid frontmatter in {skill_name}")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        require(bool(separator), f"Invalid frontmatter line in {skill_name}: {line}")
        fields[key.strip()] = value.strip()
    require(fields.get("name") == skill_name, f"Frontmatter name mismatch in {skill_name}")
    require(fields.get("description"), f"Missing description in {skill_name}")
    return fields


def validate_skills() -> None:
    skills_root = ROOT / "skills"
    skill_paths = sorted(skills_root.glob("*/SKILL.md"))
    require(skill_paths, "No packaged skills found")
    names = {path.parent.name for path in skill_paths}
    require(
        {"superb-skills", "coding-preferences", "code-quality-review"} <= names,
        "Missing a required Dev Tools skill",
    )
    for skill_path in skill_paths:
        name = skill_path.parent.name
        parse_frontmatter(read(skill_path), name)
        agent = read(skill_path.parent / "agents" / "openai.yaml")
        for field in ("display_name:", "short_description:", "default_prompt:"):
            require(field in agent, f"Missing {field} in {name}/agents/openai.yaml")
        require(f"${name}" in agent, f"Default prompt does not name ${name}")


def validate_links() -> None:
    pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for markdown in ROOT.rglob("*.md"):
        for raw_target in pattern.findall(read(markdown)):
            target = raw_target.strip().split()[0].strip("<>")
            if "://" in target or target.startswith(("#", "mailto:")):
                continue
            path = target.split("#", 1)[0].split("?", 1)[0]
            if not path:
                continue
            require((markdown.parent / path).resolve().is_file(), f"Broken link in {markdown.relative_to(ROOT)}: {target}")


def validate_skill_package() -> None:
    skill = ROOT / "skills" / "superb-skills"
    required = (
        "agents/openai.yaml", "assets/icon-small.svg", "assets/icon-large.svg",
        "references/evaluation-input-contract.md", "references/evaluation.md",
        "references/instruction-design.md", "references/plugin-architecture.md",
        "references/preferences-and-lessons.md", "references/project-instructions-template.md",
        "references/benchmark-advisory/design.md", "references/benchmark-advisory/review.md",
        "references/working-memory.md", "scripts/check_instruction_length.py",
        "scripts/compare_candidates.py",
    )
    for relative in required:
        read(skill / relative)
    suite = json.loads(read(ROOT / "evals" / "superb-skills-evaluation.json"))
    for field in ("fixture_manifest", "cases", "suite_id", "suite_version"):
        require(suite.get(field), f"Evaluation suite missing {field}")
    fixture_path = ROOT.parent.parent / suite["fixture_manifest"]
    require(fixture_path.is_file(), "Evaluation fixture manifest path does not resolve from repository root")
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
    require(fixtures.get("fixture_id") == "superb-skills-fixtures", "Unexpected fixture manifest")
    designer_plan = next(plan for plan in fixtures["partition_policy"]["plans"] if plan.get("scope") == "designer_quality")
    require((fixture_path.parent / designer_plan["case_source"]).resolve() == (ROOT / "evals" / "superb-skills-evaluation.json").resolve(), "Designer case source does not resolve to the packaged suite")
    for target in fixtures["targets"]:
        target_root = fixture_path.parent / target["path"]
        for relative in target["content_files"]:
            require((target_root / relative).is_file(), f"Missing fixture target file: {target['id']}/{relative}")
    for artifact in fixtures["artifacts"]:
        require((fixture_path.parent / artifact["path"]).is_file(), f"Missing fixture artifact: {artifact['id']}")


def validate_issue_30_skills() -> None:
    requirements = {
        "code-quality-review": (
            "SKILL.md", "agents/openai.yaml", "references/reviewer.md",
            "assets/icon-small.svg", "assets/icon-large.svg",
        ),
    }
    for name, resources in requirements.items():
        root = ROOT / "skills" / name
        skill = read(root / "SKILL.md")
        parse_frontmatter(skill, name)
        agent = read(root / "agents" / "openai.yaml")
        require("dependencies:" not in agent, f"Unexpected external dependency in {name}/agents/openai.yaml")
        contents = {"SKILL.md": skill, "agents/openai.yaml": agent}
        for relative in resources:
            if relative not in contents:
                contents[relative] = read(root / relative)
        for asset, expected in (("icon-small.svg", ("24", "24", "0 0 24 24")), ("icon-large.svg", ("64", "64", "0 0 64 64"))):
            element = ET.fromstring(contents[f"assets/{asset}"])
            require((element.get("width"), element.get("height"), element.get("viewBox")) == expected, f"Unexpected {name} icon dimensions: {asset}")


def validate_coding_preferences() -> None:
    root = ROOT / "skills" / "coding-preferences"
    skill = read(root / "SKILL.md")
    parse_frontmatter(skill, "coding-preferences")
    agent = read(root / "agents" / "openai.yaml")
    for field in ("icon_small: \"./assets/icon-small.svg\"", "icon_large: \"./assets/icon-large.svg\""):
        require(field in agent, f"Coding Preferences metadata missing {field}")
    for asset, expected in (("icon-small.svg", ("24", "24", "0 0 24 24")), ("icon-large.svg", ("64", "64", "0 0 64 64"))):
        svg = root / "assets" / asset
        require(svg.is_file(), f"Missing Coding Preferences icon: {asset}")
        element = ET.parse(svg).getroot()
        require((element.get("width"), element.get("height"), element.get("viewBox")) == expected, f"Unexpected icon dimensions: {asset}")

    record_guide = read(root / "references" / "record-management.md")
    workflow = read(root / "references" / "coding-workflow.md")
    require("coding-preferences/v1" in record_guide, "Missing Markdown record format")
    require("do not edit project instructions automatically" in record_guide.lower(), "Missing separate pointer-authorization boundary")
    require("at most one reconciled retry" in record_guide.lower(), "Missing bounded uncertain-write recovery")
    require("repository instructions" in workflow and "verified relevant coding preferences" in workflow, "Missing coding preference precedence")

    fixture_root = ROOT / "evals" / "coding-preferences" / "fixtures"
    before = read(fixture_root / "coding-preferences-before.md")
    after = read(fixture_root / "coding-preferences-after.md")
    require("CP-PY-001" in before and "CP-PY-001" in after, "Missing preserved Python fixture entry")
    require("snake_case for local variable names" in before and "snake_case for local variable names" in after, "Python fixture entry changed")
    require("lowercase SQL keywords" in before and "uppercase SQL keywords" in after, "SQL fixture does not show the authorized update")
    require(not list(fixture_root.rglob("*.yaml")) and not list(fixture_root.rglob("*.yml")), "Preference fixtures must remain Markdown")


def validate_regression() -> None:
    suite = json.loads(read(ROOT / "evals" / "regression.json"))
    require(suite.get("suite") == "dev-tools-regression", "Unexpected Dev Tools regression suite")
    ids: set[str] = set()
    for case in suite.get("cases", []):
        case_id = case.get("id")
        require(case_id and case_id not in ids, f"Duplicate or missing eval id: {case_id}")
        ids.add(case_id)
        for field in ("input", "intended_behavior", "success_criteria", "failure_criteria"):
            require(case.get(field), f"{case_id} missing {field}")
    for case_id in (
        "route-superb-skills", "instruction-hard-limit", "memory-recall-before-token-reduction", "memory-audit-success",
        "coding-sql-save-preserves-python", "coding-fresh-session-pointer", "coding-repository-rule-wins",
        "coding-explicit-override-surfaces-conflict", "coding-one-time-override", "coding-unknown-destination-no-write",
        "coding-review-only-no-edit", "coding-explanation-only-no-tools", "coding-no-tool-preserved",
        "coding-inline-value-is-task-local",
        "coding-writing-context-targeted", "coding-remember-me-unknown-setup-neutral",
        "coding-owner-transfer-verifies-before-reconcile",
        "benchmark-critique-direct", "benchmark-design-interview",
        "benchmark-instruction-evaluation-single-owner", "benchmark-mixed-instruction-evaluation",
        "quality-review-requested", "quality-review-preferences-only-when-unresolved",
        "quality-review-ordinary-coding-no-review", "quality-review-no-tool",
        "quality-review-preferences-unavailable",
    ):
        require(case_id in ids, f"Missing required Dev Tools eval: {case_id}")


def main() -> int:
    checks = (validate_manifest, validate_skills, validate_links, validate_skill_package, validate_coding_preferences, validate_issue_30_skills, validate_regression)
    for check in checks:
        check()
        print(f"PASS {check.__name__}")
    print("PASS dev-tools plugin validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
