"""Resource and design-interview checks for Superb Skills benchmark advice."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "superb-skills"


def test_benchmark_advisory_resources_are_linked_and_resolve() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    references = (
        SKILL_DIR / "references" / "benchmark-advisory" / "review.md",
        SKILL_DIR / "references" / "benchmark-advisory" / "design.md",
    )

    for reference in references:
        assert reference.is_file()
        source = reference.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", source):
            if target.startswith(("https://", "http://", "mailto:")):
                continue
            local_target = target.split("#", maxsplit=1)[0]
            if local_target:
                assert (reference.parent / local_target).resolve().is_file(), target

    assert "references/benchmark-advisory/review.md" in skill
    assert "references/benchmark-advisory/design.md" in skill


def test_benchmark_design_asks_before_resolving_material_unknowns() -> None:
    design = (
        SKILL_DIR / "references" / "benchmark-advisory" / "design.md"
    ).read_text(encoding="utf-8").lower()

    assert "end that response with the question and wait for their answer" in design
    assert "make the actual question the last content in the response and stop there" in design
    assert "do not select a provisional framing in the same response" in design
    assert "latest explicit answer as settled" in design
    assert "do not turn an answered detail into an unknown" in design
    assert "reuse answers already supplied" in design
    assert "stop at a useful provisional design" in design


def test_benchmark_review_qualifies_claims_and_keeps_modes_distinct() -> None:
    review = (
        SKILL_DIR / "references" / "benchmark-advisory" / "review.md"
    ).read_text(encoding="utf-8").lower()

    for label in ("observation:", "inference:", "unknown or limitation:"):
        assert label in review
    assert "single aggregate" in review
    assert "does not by itself establish variability" in review
    assert "do not turn an explanation request into an interview" in review
