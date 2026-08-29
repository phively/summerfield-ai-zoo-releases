#!/usr/bin/env python3
"""Deterministic structural validation for the work-smarter plugin."""

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("remember-me", "research-briefing", "superb-skills", "teach-me")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read(path: Path) -> str:
    require(path.is_file(), f"Missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def validate_manifest() -> None:
    manifest = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))
    require(manifest["name"] == "work-smarter", "Unexpected plugin name")
    require(manifest["skills"] == "./skills/", "Unsupported skills path")
    for field in ("version", "description", "author", "interface"):
        require(field in manifest, f"Missing manifest field: {field}")
    interface = manifest["interface"]
    for field in (
        "displayName", "shortDescription", "longDescription", "developerName",
        "category", "capabilities", "brandColor", "composerIcon", "logo",
        "defaultPrompt",
    ):
        require(field in interface, f"Missing interface field: {field}")
    for field in ("composerIcon", "logo"):
        path = ROOT / interface[field].removeprefix("./")
        require(path.is_file(), f"Missing interface asset: {interface[field]}")


def parse_frontmatter(text: str, skill: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    require(match is not None, f"Invalid frontmatter in {skill}")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        require(bool(separator), f"Invalid frontmatter line in {skill}: {line}")
        fields[key.strip()] = value.strip()
    require(set(fields) == {"name", "description"}, f"Unexpected frontmatter fields in {skill}")
    require(fields["name"] == skill, f"Frontmatter name mismatch in {skill}")
    require(bool(fields["description"]), f"Missing description in {skill}")
    return fields


def validate_skills() -> None:
    for skill in SKILLS:
        root = ROOT / "skills" / skill
        text = read(root / "SKILL.md")
        parse_frontmatter(text, skill)
        agent = read(root / "agents" / "openai.yaml")
        for field in ("display_name:", "short_description:", "default_prompt:"):
            require(field in agent, f"Missing {field} in {skill}/agents/openai.yaml")
        require(f"${skill}" in agent, f"Default prompt does not name ${skill}")


def validate_links() -> None:
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for markdown in ROOT.rglob("*.md"):
        for target in pattern.findall(read(markdown)):
            if "://" in target or target.startswith("#"):
                continue
            path = target.split("#", 1)[0]
            require((markdown.parent / path).resolve().is_file(), f"Broken link in {markdown.relative_to(ROOT)}: {target}")


def validate_contract() -> None:
    contract = read(ROOT / "shared" / "handoff-contracts.md")
    for phrase in (
        "Invoking skill", "Receiving skill", "Trigger", "Required input",
        "Expected output", "Authority and provenance", "Uncertainty",
        "Failure behavior", "Information not to pass", "User confirmation",
        "research-scope checkpoint", "`work-smarter` bundles and maintains",
        "Teach Me to Research Briefing",
        "Bundled Skills to Remember Me: targeted consultation",
        "Bundled Skills to Remember Me: durable update request",
        "Remember Me to External Domain Owner", "No reverse handoff",
    ):
        require(phrase in contract, f"Contract missing: {phrase}")


def validate_remember_me() -> None:
    root = ROOT / "skills" / "remember-me"
    skill = read(root / "SKILL.md")
    records = read(root / "references" / "record-management.md")
    require("TODO" not in skill, "remember-me contains scaffold TODOs")
    for phrase in (
        "remember-me/index.md", "convenience cache", "current-task override",
        "remember-me/history.md", "Never store passwords",
    ):
        require(phrase in skill, f"remember-me missing behavior: {phrase}")
    for phrase in (
        "communication-collaboration.md", "entertainment-interests.md",
        "career-coach:career-direction", "meal-planner:personal-chef",
        "RMH-YYYY-MM-DD-NN",
    ):
        require(phrase in records, f"remember-me records missing: {phrase}")
    require(not (root / "index.md").exists(), "Packaged skill must not contain personal index data")
    require(not (root / "history.md").exists(), "Packaged skill must not contain personal history data")


def validate_teach_me() -> None:
    root = ROOT / "skills" / "teach-me"
    skill = read(root / "SKILL.md")
    workflow = read(root / "references" / "teaching-workflow.md")
    personality = read(root / "references" / "personalities" / "nicer-socrates.md")
    for phrase in (
        "Complete the research before substantive teaching begins",
        "fall back to `nicer-socrates.md`",
        "Do not persist lesson transcripts",
        "Correct a consequential false premise",
    ):
        require(phrase in skill, f"teach-me missing behavior: {phrase}")
    for phrase in (
        "question only when its answer could",
        "A chain of reasonable answers can still drift",
        "Do not claim mastery",
    ):
        require(phrase in workflow, f"teach-me workflow missing: {phrase}")
    for phrase in (
        "resisting reflexive agreement",
        "Ask one question at a time",
        "constitutive of the concept",
        "Skip directly to explanation",
    ):
        require(phrase in personality, f"nicer-socrates missing: {phrase}")


def validate_memory_priorities() -> None:
    superb = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    memory = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    contract = read(ROOT / "shared" / "handoff-contracts.md")
    priorities = (
        "1. Preserve reliable recall",
        "2. Minimize the tokens",
        "3. Minimize the time",
    )
    positions = [memory.index(priority) for priority in priorities]
    require(positions == sorted(positions), "Memory priorities are out of order")
    for phrase, artifact in (
        ("Never trade a higher-ranked objective", superb),
        ("Never improve a lower-ranked objective", memory),
        ("Reliable recall takes priority", remember),
        ("Keep the transaction narrow only when", records),
        ("Expand beyond the index summary", contract),
    ):
        require(phrase in artifact, f"Memory priority guidance missing: {phrase}")


def validate_memory_audit_guidance() -> None:
    superb = read(ROOT / "skills" / "superb-skills" / "SKILL.md")
    memory = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    audit_script = ROOT / "scripts" / "validate_memory_audit.py"
    require(audit_script.is_file(), "Missing deterministic memory audit validator")
    for phrase, artifact in (
        ("measurable lifecycle-review trigger", superb),
        ("conservative default design heuristic", memory),
        ("8 KiB", records),
        ("180 days", records),
        ("25 material changes", records),
        ("bounded retrieval", records),
        ("Conversation-context compaction", records),
        ("immutable resource", records),
        ("canonical permalink", records),
        ("bidirectional ledger", memory),
        ("A due trigger requires review, not automatic", remember),
        ("explicit or implicit comparison", research),
        ("supported absolute property", research),
        ("opening summary name and directly link", research),
        ("what each reference influenced", research),
        ("Do not propose or create phases by default", research),
        ("silence does not authorize research", research),
        ("A progress update is not a completed checkpoint", research),
    ):
        require(phrase in artifact, f"Memory audit or research summary guidance missing: {phrase}")


def validate_evals() -> None:
    suite = json.loads(read(ROOT / "evals" / "regression.json"))
    require(suite["suite"] == "work-smarter-regression", "Unexpected eval suite")
    require(len(suite["cases"]) >= 12, "Regression suite is too small")
    ids = set()
    for case in suite["cases"]:
        require(case["id"] not in ids, f"Duplicate eval id: {case['id']}")
        ids.add(case["id"])
        for field in ("input", "intended_behavior", "success_criteria", "failure_criteria"):
            require(case.get(field), f"{case['id']} missing {field}")
    for case_id in (
        "memory-recall-before-token-reduction",
        "memory-token-reduction-before-speed",
        "memory-narrow-update-fallback",
        "memory-maintenance-trigger",
        "memory-audit-success",
        "memory-audit-loss-failure",
        "research-opening-influential-sources",
        "research-large-request-phase-choice",
        "research-ordinary-request-no-phase-warning",
        "research-phase-choice-default-continuous",
        "research-phase-checkpoint-no-response",
        "research-phased-work-stops-after-log",
        "research-waiver-no-phase-pause",
        "research-unsupported-implicit-comparison",
        "research-supported-comparison",
        "research-subjective-comparison",
        "memory-nonsize-audit-trigger",
        "memory-context-vs-record-compaction",
        "memory-conditional-toc",
        "memory-provider-identity-pointer",
    ):
        require(case_id in ids, f"Missing required eval: {case_id}")
    results = json.loads(read(ROOT / "evals" / "results.json"))
    require(results["plugin_version"] == "1.6.0", "Unexpected results version")
    require(len(results["forward_tests"]) >= 4, "Missing forward-test results")


def main() -> int:
    checks = (
        validate_manifest, validate_skills, validate_links,
        validate_contract, validate_remember_me, validate_teach_me, validate_memory_priorities,
        validate_memory_audit_guidance, validate_evals,
    )
    for check in checks:
        check()
        print(f"PASS {check.__name__}")
    print("PASS work-smarter plugin validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
