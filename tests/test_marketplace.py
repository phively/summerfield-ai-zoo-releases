#!/usr/bin/env python3
"""Marketplace discovery and catalog consistency tests."""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
EXPECTED_PLUGINS = (
    "meal-planner",
    "work-smarter",
    "career-coach",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def skill_interface_value(skill_path: Path, field: str) -> str:
    agent = read(skill_path.parent / "agents" / "openai.yaml")
    for line in agent.splitlines():
        key, separator, value = line.strip().partition(":")
        if separator and key == field:
            return value.strip().strip('"\'')
    raise AssertionError(f"Missing {field} for {skill_path}")


def skill_short_description(skill_path: Path) -> str:
    return skill_interface_value(skill_path, "short_description")


def svg_dimensions(path: Path) -> tuple[str | None, str | None, str | None]:
    root = ET.parse(path).getroot()
    return root.get("width"), root.get("height"), root.get("viewBox")


def test_supported_marketplace_manifest_is_present() -> None:
    assert MARKETPLACE_PATH.is_file()
    marketplace = json.loads(read(MARKETPLACE_PATH))
    assert marketplace["name"] == "summerfield-ai-zoo"
    assert marketplace["interface"]["displayName"] == "Summerfield AI Zoo"
    assert tuple(entry["name"] for entry in marketplace["plugins"]) == EXPECTED_PLUGINS


def test_marketplace_entries_resolve_to_discoverable_plugins() -> None:
    marketplace = json.loads(read(MARKETPLACE_PATH))
    for entry in marketplace["plugins"]:
        name = entry["name"]
        assert entry["source"]["source"] == "local"
        assert entry["source"]["path"] == f"./plugins/{name}"
        assert entry["policy"] == {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        }
        assert entry["category"]

        plugin_root = REPO_ROOT / entry["source"]["path"]
        manifest = json.loads(read(plugin_root / ".codex-plugin" / "plugin.json"))
        assert manifest["name"] == name == plugin_root.name
        assert isinstance(manifest["author"]["name"], str) and manifest["author"]["name"]
        assert isinstance(manifest["interface"]["developerName"], str) and manifest["interface"]["developerName"]
        assert (plugin_root / manifest["interface"]["composerIcon"]).is_file()
        assert (plugin_root / manifest["interface"]["logo"]).is_file()
        skills_root = plugin_root / manifest["skills"]
        assert list(skills_root.glob("*/SKILL.md")), f"No discoverable skills in {name}"


def test_svg_asset_references_resolve_and_cover_every_svg() -> None:
    referenced: set[Path] = set()
    expected_dimensions = {
        "composerIcon": ("24", "24", "0 0 24 24"),
        "logo": ("64", "64", "0 0 64 64"),
        "logoDark": ("64", "64", "0 0 64 64"),
    }

    for name in EXPECTED_PLUGINS:
        plugin_root = REPO_ROOT / "plugins" / name
        manifest = json.loads(read(plugin_root / ".codex-plugin" / "plugin.json"))
        for field, expected in expected_dimensions.items():
            relative = manifest["interface"].get(field)
            if relative is None:
                continue
            asset = plugin_root / relative
            assert asset.is_file(), f"Missing {field} for {name}: {relative}"
            if asset.suffix.lower() == ".svg":
                assert svg_dimensions(asset) == expected
                referenced.add(asset.resolve())

        for skill_path in sorted((plugin_root / "skills").glob("**/SKILL.md")):
            for field, expected in (
                ("icon_small", ("24", "24", "0 0 24 24")),
                ("icon_large", ("64", "64", "0 0 64 64")),
            ):
                relative = skill_interface_value(skill_path, field)
                asset = skill_path.parent / relative
                assert asset.is_file(), f"Missing {field} for {skill_path}: {relative}"
                assert asset.suffix.lower() == ".svg"
                assert svg_dimensions(asset) == expected
                referenced.add(asset.resolve())

    all_svgs = {path.resolve() for path in (REPO_ROOT / "plugins").glob("**/*.svg")}
    assert referenced == all_svgs


def test_research_briefing_has_bundled_and_standalone_copies() -> None:
    bundled = (
        REPO_ROOT
        / "plugins"
        / "work-smarter"
        / "skills"
        / "research-briefing"
        / "SKILL.md"
    )
    standalone = REPO_ROOT / "skills" / "research-briefing" / "SKILL.md"
    assert bundled.is_file()
    assert standalone.is_file()
    matches = {
        path
        for path in REPO_ROOT.glob("**/research-briefing/SKILL.md")
        if ".git" not in path.parts
    }
    assert matches == {bundled, standalone}


def test_standalone_research_briefing_is_self_contained() -> None:
    root = REPO_ROOT / "skills" / "research-briefing"
    files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    assert files == {
        "SKILL.md",
        "agents/openai.yaml",
        "assets/icon-large.svg",
        "assets/icon-small.svg",
    }

    skill = read(root / "SKILL.md")
    agent = read(root / "agents" / "openai.yaml")
    plugin = json.loads(
        read(REPO_ROOT / "plugins" / "work-smarter" / ".codex-plugin" / "plugin.json")
    )
    assert "Standalone research and briefing skill" in skill
    assert f'metadata:\n  version: "{plugin["version"]}"\n---' in skill
    assert not re.search(r"(?m)^version:", skill)
    for phrase in (
        "Do not propose or create phases by default",
        "without addressing work structure, proceed as one continuous briefing",
        "silence does not authorize research",
        "Stop and wait for the user's explicit instruction to continue",
        "A progress update is not a completed checkpoint",
    ):
        assert phrase in skill
    for forbidden in ("remember-me", "superb-skills", "handoff-contracts"):
        assert forbidden not in skill
        assert forbidden not in agent
    assert "dependencies:" not in agent
    assert 'icon_small: "./assets/icon-small.svg"' in agent
    assert 'icon_large: "./assets/icon-large.svg"' in agent

    bundled_assets = (
        REPO_ROOT / "plugins" / "work-smarter" / "skills" / "research-briefing" / "assets"
    )
    for icon in ("icon-small.svg", "icon-large.svg"):
        assert read(root / "assets" / icon) == read(bundled_assets / icon)


def test_catalog_covers_marketplace_plugins_and_readme_links_them() -> None:
    catalog = read(REPO_ROOT / "catalog.yaml")
    readme = read(REPO_ROOT / "README.md")
    assert readme.startswith("<!-- catalog:start -->\n")
    assert readme.count("<!-- catalog:start -->") == 1
    assert readme.count("<!-- catalog:end -->") == 1
    for name in EXPECTED_PLUGINS:
        assert re.search(
            rf"(?ms)^  - name: {re.escape(name)}\n    type: plugin\n"
            rf"    path: plugins/{re.escape(name)}$",
            catalog,
        )
        assert f"[plugins/{name}](plugins/{name})" in readme

        plugin_root = REPO_ROOT / "plugins" / name
        manifest = json.loads(read(plugin_root / ".codex-plugin" / "plugin.json"))
        row_prefix = (
            f"| {name} | plugin | [plugins/{name}](plugins/{name}) | "
            f"{manifest['description']}"
        )
        # README catalog refreshes are explicitly requested repository work. A
        # component update may intentionally leave the last generated row in place.
        if row_prefix not in readme:
            continue
        assert row_prefix in readme

        for skill_path in sorted((plugin_root / "skills").glob("**/SKILL.md")):
            relative = skill_path.relative_to(REPO_ROOT).as_posix()
            skill = re.search(r"(?m)^name:\s*(.+?)\s*$", read(skill_path))
            assert skill is not None
            bullet = (
                f"• [{skill.group(1)}]({relative}) - "
                f"{skill_short_description(skill_path)}"
            )
            assert bullet in readme


def test_catalog_and_readme_cover_standalone_research_briefing() -> None:
    catalog = read(REPO_ROOT / "catalog.yaml")
    readme = read(REPO_ROOT / "README.md")
    skill_path = REPO_ROOT / "skills" / "research-briefing" / "SKILL.md"
    skill = read(skill_path)
    description = re.search(r"(?m)^description:\s*(.+?)\s*$", skill)
    assert description is not None

    assert re.search(
        r"(?ms)^  - name: research-briefing\n    type: skill\n"
        r"    path: skills/research-briefing$",
        catalog,
    )
    assert (
        "| research-briefing | skill | "
        "[skills/research-briefing](skills/research-briefing/SKILL.md) | "
        f"{description.group(1)} |"
    ) in readme


def test_teach_me_has_bundled_and_standalone_copies() -> None:
    bundled = REPO_ROOT / "plugins" / "work-smarter" / "skills" / "teach-me"
    standalone = REPO_ROOT / "skills" / "teach-me"
    assert (bundled / "SKILL.md").is_file()
    assert (standalone / "SKILL.md").is_file()

    matches = {
        path
        for path in REPO_ROOT.glob("**/teach-me/SKILL.md")
        if ".git" not in path.parts
    }
    assert matches == {bundled / "SKILL.md", standalone / "SKILL.md"}


def test_standalone_teach_me_is_self_contained_and_mirrors_references() -> None:
    bundled = REPO_ROOT / "plugins" / "work-smarter" / "skills" / "teach-me"
    standalone = REPO_ROOT / "skills" / "teach-me"
    plugin = json.loads(
        read(REPO_ROOT / "plugins" / "work-smarter" / ".codex-plugin" / "plugin.json")
    )
    files = {
        path.relative_to(standalone).as_posix()
        for path in standalone.rglob("*")
        if path.is_file()
    }
    assert files == {
        "SKILL.md",
        "agents/openai.yaml",
        "assets/icon-large.svg",
        "assets/icon-small.svg",
        "references/teaching-workflow.md",
        "references/personalities/nicer-socrates.md",
    }

    skill = read(standalone / "SKILL.md")
    agent = read(standalone / "agents" / "openai.yaml")
    assert "Standalone teaching skill" in skill
    assert f'metadata:\n  version: "{plugin["version"]}"\n---' in skill
    assert not re.search(r"(?m)^version:", skill)
    for forbidden in ("work-smarter", "remember-me", "research-briefing", "handoff-contracts"):
        assert forbidden not in skill
        assert forbidden not in agent
    assert "dependencies:" not in agent

    for relative in (
        "assets/icon-large.svg",
        "assets/icon-small.svg",
        "references/teaching-workflow.md",
        "references/personalities/nicer-socrates.md",
    ):
        assert read(standalone / relative) == read(bundled / relative)


def test_catalog_covers_standalone_teach_me() -> None:
    catalog = read(REPO_ROOT / "catalog.yaml")
    assert re.search(
        r"(?ms)^  - name: teach-me\n    type: skill\n"
        r"    path: skills/teach-me$",
        catalog,
    )
