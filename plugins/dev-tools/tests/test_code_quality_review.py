"""Resource and handoff-boundary checks for Code Quality Review."""

import re
from pathlib import Path
import xml.etree.ElementTree as ET


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = PLUGIN_ROOT / "skills" / "code-quality-review"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(content: str, heading: str, next_heading: str) -> str:
    start = content.index(heading) + len(heading)
    end = content.index(next_heading, start)
    return content[start:end]


def test_entrypoint_resources_and_icons_resolve_locally() -> None:
    skill = read(SKILL_ROOT / "SKILL.md")
    assert skill.startswith("---\nname: code-quality-review\n")
    assert "references/reviewer.md" in skill
    assert "../../shared/handoff-contracts.md#caller-to-code-quality-review-bounded-review-request" in skill
    assert (SKILL_ROOT / "references" / "reviewer.md").is_file()

    metadata = read(SKILL_ROOT / "agents" / "openai.yaml")
    assert 'display_name: "Code Quality Review"' in metadata
    assert 'short_description: "Evidence-backed review of requested code changes"' in metadata
    assert 'default_prompt: "Use $code-quality-review ' in metadata
    for filename, dimensions in (
        ("icon-small.svg", ("24", "24", "0 0 24 24")),
        ("icon-large.svg", ("64", "64", "0 0 64 64")),
    ):
        svg = ET.parse(SKILL_ROOT / "assets" / filename).getroot()
        assert (svg.get("width"), svg.get("height"), svg.get("viewBox")) == dimensions


def test_skill_is_optional_and_no_tool_reviews_stay_with_supplied_content() -> None:
    skill = read(SKILL_ROOT / "SKILL.md").lower()
    assert "only for a requested code-quality review or after the user accepts" in skill
    assert "ordinary implementation or coding-preference work" in skill
    assert "no-tool request uses supplied content only" in skill
    assert "do not read files, run commands, retrieve preferences, or spawn a reviewer" in skill


def test_request_packet_binds_findings_to_captured_scope() -> None:
    guide = read(SKILL_ROOT / "references" / "reviewer.md")
    packet = section(guide, "## Capture the request and target", "## Review the bounded scope")
    for required in ("review question and intended behavior", "exact target and scope", "allowed operations"):
        assert required in packet
    assert "base/head commits" in packet
    assert "included untracked files" in packet
    assert "captured staged and unstaged changes" in packet
    assert "target changes after capture" in packet


def test_result_keeps_findings_and_check_evidence_bounded() -> None:
    guide = read(SKILL_ROOT / "references" / "reviewer.md")
    result = guide.split("## Return the review", 1)[1]
    for required in ("location", "evidence", "consequence", "bounded remedy"):
        assert required in result
    assert "optional style or cleanup suggestions in a separate section" in result
    assert "observed" in result and "proposed checks" in result
    assert "do not imply the code is defect-free" in result


def test_delegation_is_single_and_independence_limits_are_explicit() -> None:
    guide = read(SKILL_ROOT / "references" / "reviewer.md")
    delegation = section(guide, "## Optional bounded delegation", "## Return the review")
    assert "one separate generic host child agent" in delegation
    assert "Do not dispatch nested agents" in delegation
    assert "label the route as same-agent" in delegation
    assert "report that requirement unmet" in delegation
    assert "disclose the incomplete pass" in delegation
    assert "When tools are prohibited, do not spawn a child" in delegation


def test_private_guide_links_only_to_public_convention_consultation() -> None:
    guide_path = SKILL_ROOT / "references" / "reviewer.md"
    guide = read(guide_path)
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", guide)
    convention_links = [link for link in links if "handoff-contracts.md#" in link]
    assert convention_links == [
        "../../../shared/handoff-contracts.md#code-quality-review-to-coding-preferences-optional-convention-consultation"
    ]
    target = (guide_path.parent / convention_links[0].split("#", 1)[0]).resolve()
    assert target.is_file()
