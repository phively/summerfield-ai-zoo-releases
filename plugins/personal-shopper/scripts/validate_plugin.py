#!/usr/bin/env python3
"""Validate the Personal Shopper plugin's manifest and packaged local resources."""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "personal-shopper"
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read(path: Path) -> str:
    require(path.is_file(), f"Missing package resource: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def local_resource(relative: str, label: str) -> Path:
    path = (ROOT / relative.removeprefix("./")).resolve()
    require(path.is_relative_to(ROOT.resolve()), f"{label} escapes the plugin package: {relative}")
    require(path.is_file(), f"Missing {label}: {relative}")
    return path


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    require(match is not None, "Invalid Personal Shopper skill frontmatter")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        require(bool(separator), f"Invalid skill frontmatter line: {line}")
        fields[key.strip()] = value.strip().strip("\"'")
    require(fields.get("name") == SKILL_NAME, "Unexpected Personal Shopper skill name")
    require(fields.get("description"), "Missing Personal Shopper skill description")
    return fields


def parse_agent_resource(agent_text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", agent_text)
    require(match is not None and match.group(1).strip(), f"Missing {key} in skill agent metadata")
    return match.group(1).strip()


def validate_svg(path: Path, dimensions: tuple[str, str, str]) -> None:
    root = ET.parse(path).getroot()
    actual = (root.get("width"), root.get("height"), root.get("viewBox"))
    require(actual == dimensions, f"Unexpected SVG dimensions for {path.relative_to(ROOT)}: {actual}")


def validate_manifest_and_assets() -> set[Path]:
    manifest_path = ROOT / ".codex-plugin" / "plugin.json"
    manifest = json.loads(read(manifest_path))
    require(manifest.get("name") == "personal-shopper", "Unexpected plugin name")
    require(manifest.get("skills") == "./skills/", "Unsupported packaged skills path")
    for field in ("version", "description", "author", "interface"):
        require(manifest.get(field), f"Missing manifest field: {field}")

    interface = manifest["interface"]
    for field in (
        "displayName", "shortDescription", "longDescription", "developerName",
        "category", "capabilities", "brandColor", "composerIcon", "logo", "defaultPrompt",
    ):
        require(interface.get(field), f"Missing plugin interface field: {field}")

    referenced_assets: set[Path] = set()
    for field, dimensions in (
        ("composerIcon", ("24", "24", "0 0 24 24")),
        ("logo", ("64", "64", "0 0 64 64")),
    ):
        asset = local_resource(interface[field], field)
        require(asset.suffix.lower() == ".svg", f"{field} must be an SVG")
        validate_svg(asset, dimensions)
        referenced_assets.add(asset.resolve())

    skills = sorted((ROOT / "skills").glob("**/SKILL.md"))
    require(len(skills) == 1, "Personal Shopper must package exactly one skill")
    skill_path = skills[0]
    require(skill_path.parent.name == SKILL_NAME, "Skill directory must match its qualified entry point")
    parse_frontmatter(read(skill_path))

    agent_path = skill_path.parent / "agents" / "openai.yaml"
    agent_text = read(agent_path)
    for key, dimensions in (
        ("icon_small", ("24", "24", "0 0 24 24")),
        ("icon_large", ("64", "64", "0 0 64 64")),
    ):
        relative = parse_agent_resource(agent_text, key)
        asset = local_resource(str((skill_path.parent / relative).relative_to(ROOT)), key)
        require(asset.suffix.lower() == ".svg", f"{key} must be an SVG")
        validate_svg(asset, dimensions)
        referenced_assets.add(asset.resolve())

    all_assets = {path.resolve() for path in ROOT.rglob("*") if path.is_file() and "assets" in path.relative_to(ROOT).parts}
    require(referenced_assets == all_assets,
            f"Asset references do not match packaged assets; unreferenced={sorted(str(p.relative_to(ROOT)) for p in all_assets - referenced_assets)}, missing={sorted(str(p.relative_to(ROOT)) for p in referenced_assets - all_assets)}")
    return referenced_assets


def validate_local_markdown_links() -> None:
    for markdown in sorted(ROOT.rglob("*.md")):
        for raw_target in LINK_PATTERN.findall(read(markdown)):
            target = raw_target.strip().split()[0].strip("<>")
            parsed = urlparse(target)
            if parsed.scheme or target.startswith(("#", "mailto:")):
                continue
            local_target = parsed.path.split("#", 1)[0]
            if not local_target:
                continue
            resolved = (markdown.parent / local_target).resolve()
            require(resolved.is_relative_to(ROOT.resolve()),
                    f"Package link escapes Personal Shopper: {markdown.relative_to(ROOT)} -> {target}")
            require(resolved.is_file(),
                    f"Broken package link in {markdown.relative_to(ROOT)}: {target}")


def validate_package_boundary() -> None:
    manifest = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))
    require("dependencies" not in manifest,
            "Do not add unsupported plugin dependency metadata")
    for markdown in ROOT.rglob("*.md"):
        text = read(markdown)
        require("plugins/meal-planner/" not in text,
                f"Runtime link to Meal Planner internals in {markdown.relative_to(ROOT)}")


def main() -> int:
    validate_manifest_and_assets()
    print("PASS manifest and declared assets")
    validate_local_markdown_links()
    print("PASS package-local Markdown links")
    validate_package_boundary()
    print("PASS independent package boundary")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, json.JSONDecodeError, ET.ParseError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
