import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parents[1]


def test_plugin_validator_accepts_the_packaged_resources() -> None:
    result = subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "scripts" / "validate_plugin.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS manifest and declared assets" in result.stdout
    assert "PASS package-local Markdown links" in result.stdout
    assert "PASS independent package boundary" in result.stdout


def test_package_has_one_independent_skill_and_no_invented_dependencies() -> None:
    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    skill_paths = sorted((PLUGIN_ROOT / "skills").glob("**/SKILL.md"))

    assert manifest["name"] == "personal-shopper"
    assert manifest["skills"] == "./skills/"
    assert "dependencies" not in manifest
    assert len(skill_paths) == 1
    assert skill_paths[0].parent.name == "personal-shopper"


def test_host_readable_skill_contains_its_transitive_contracts() -> None:
    skill = PLUGIN_ROOT / "skills" / "personal-shopper"
    for markdown in skill.rglob("*.md"):
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", markdown.read_text(encoding="utf-8")):
            if ":" in target or target.startswith("#"):
                continue
            resolved = (markdown.parent / target.split("#", 1)[0]).resolve()
            assert resolved.is_relative_to(skill.resolve()), f"Host cannot read {markdown.name}: {target}"
            assert resolved.is_file()

    for source in (PLUGIN_ROOT / "shared").glob("*.md"):
        expected = source.read_text(encoding="utf-8").replace(
            "../skills/personal-shopper/references/", "../"
        ).replace("../scripts/", "../../scripts/")
        assert (skill / "references" / "contracts" / source.name).read_text(encoding="utf-8") == expected
    assert (skill / "scripts" / "validate_workbook_audit.py").read_bytes() == (
        PLUGIN_ROOT / "scripts" / "validate_workbook_audit.py"
    ).read_bytes()


def test_all_packaged_assets_are_referenced_and_valid_svg() -> None:
    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    agent = (PLUGIN_ROOT / "skills" / "personal-shopper" / "agents" / "openai.yaml").read_text(encoding="utf-8")
    import re

    agent_assets = {
        f"skills/personal-shopper/{match.group(1)}"
        for match in re.finditer(r'(?m)^\s*icon_(?:small|large):\s*["\']?([^"\'\n]+)', agent)
    }
    referenced = {
        (PLUGIN_ROOT / manifest["interface"][field].removeprefix("./")).resolve()
        for field in ("composerIcon", "logo")
    }
    referenced.update((PLUGIN_ROOT / path).resolve() for path in agent_assets)
    packaged = {
        path.resolve()
        for path in PLUGIN_ROOT.rglob("*")
        if path.is_file() and "assets" in path.relative_to(PLUGIN_ROOT).parts
    }

    assert referenced == packaged
    for path in packaged:
        assert path.suffix == ".svg"
        assert ET.parse(path).getroot().tag.endswith("svg")
