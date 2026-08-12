#!/usr/bin/env python3
"""Marketplace discovery and catalog consistency tests."""

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
EXPECTED_PLUGINS = ("meal-planner", "research-briefing", "career-coach")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
        skills_root = plugin_root / manifest["skills"]
        assert list(skills_root.glob("*/SKILL.md")), f"No discoverable skills in {name}"


def test_research_briefing_has_one_canonical_skill_copy() -> None:
    canonical = (
        REPO_ROOT
        / "plugins"
        / "research-briefing"
        / "skills"
        / "research-briefing"
        / "SKILL.md"
    )
    assert canonical.is_file()
    assert not (REPO_ROOT / "skills" / "research-briefing" / "SKILL.md").exists()
    matches = [
        path
        for path in REPO_ROOT.glob("**/research-briefing/SKILL.md")
        if ".git" not in path.parts
    ]
    assert matches == [canonical]


def test_catalog_and_readme_cover_marketplace_plugins() -> None:
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
