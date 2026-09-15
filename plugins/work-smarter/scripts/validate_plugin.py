#!/usr/bin/env python3
"""Deterministic structural validation for the work-smarter plugin."""

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("remember-me", "research-briefing", "superb-skills", "teach-me", "record-backup")


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


def validate_record_backup() -> None:
    root = ROOT / "skills" / "record-backup"
    skill = read(root / "SKILL.md")
    agent = read(root / "agents" / "openai.yaml")
    for phrase in (
        "GitHub is backup and recovery history only",
        "Discover the configured source scope independently",
        "A retrieval miss is not evidence of deletion",
        "An on-demand backup uses the daily-sync procedure",
        "weekly reconciliation",
        "independent remote read",
        "verified-no-change",
    ):
        require(phrase in skill, f"record-backup missing behavior: {phrase}")
    for reference in (
        "configuration-and-schema.md", "daily-sync.md",
        "weekly-reconciliation.md", "restore-staging.md",
    ):
        require((root / "references" / reference).is_file(), f"Missing record-backup reference: {reference}")
    require((root / "scripts" / "validate_snapshot.py").is_file(), "Missing snapshot validator")
    require("$record-backup" in agent, "Record-backup default prompt does not name $record-backup")


def validate_teach_me() -> None:
    root = ROOT / "skills" / "teach-me"
    skill = read(root / "SKILL.md")
    philosophy = read(root / "references" / "learning-philosophy.md")
    evidence = read(root / "references" / "learning-evidence.md")
    workflow = read(root / "references" / "teaching-workflow.md")
    personality = read(root / "references" / "personalities" / "nicer-socrates.md")
    visual = read(root / "references" / "domains" / "visual-arts.md")
    drawing = read(root / "references" / "domains" / "drawing-painting.md")
    for phrase in (
        "Complete the research before substantive teaching begins",
        "fall back to `nicer-socrates.md`",
        "Do not persist lesson transcripts",
        "Correct a consequential false premise",
        "task completion without a learning goal as outside this skill",
        "do not imply that the skill will return autonomously",
    ):
        require(phrase in skill, f"teach-me missing behavior: {phrase}")
    for phrase in (
        "question only when its answer could",
        "A chain of reasonable answers can still drift",
        "Do not claim mastery",
        "example-first",
        "generation-first",
        "least substitutive assistance",
        "commission",
        "omission",
    ):
        require(phrase in workflow, f"teach-me workflow missing: {phrase}")
    for phrase in (
        "Neither generation-first nor explanation-first is universally preferable",
        "Do not turn tendencies into doctrine",
        "independent capability",
        "human-tool capability",
    ):
        require(phrase in philosophy, f"teach-me philosophy missing: {phrase}")
    for phrase in (
        "Current synthesis",
        "Initial source register",
        "Candidate-source intake",
        "User-supplied claims remain attributed",
        "A due date means review is due; it does not authorize research",
    ):
        require(phrase in evidence, f"teach-me evidence missing: {phrase}")
    for phrase in (
        "resisting reflexive agreement",
        "Ask one question at a time",
        "constitutive of the concept",
        "Skip directly to explanation",
    ):
        require(phrase in personality, f"nicer-socrates missing: {phrase}")
    for phrase in (
        "without a making-skill goal",
        "Do not import drawing or painting procedures",
        "Do not assume cross-medium transfer",
        "apply the core workflow's mastery standard",
    ):
        require(phrase in visual, f"visual-arts missing behavior: {phrase}")
    for phrase in (
        "Do not load it for sculpture, ceramics, weaving",
        "Apply the shared visual-arts reference-use procedure",
        "If the artwork itself is unavailable, do not pretend to inspect it",
        "identify the intended medium or state a limited assumption",
        "Use this section only when calligraphy is part of the learning goal",
    ):
        require(phrase in drawing, f"drawing-painting missing behavior: {phrase}")
    shared_link = "](references/domains/visual-arts.md)"
    family_link = "](references/domains/drawing-painting.md)"
    require(shared_link in skill and family_link in skill, "teach-me missing visual-art domain links")
    require(skill.index(shared_link) < skill.index(family_link), "teach-me must route shared visual-art core before family")


def validate_memory_priorities() -> None:
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
        ("Never improve a lower-ranked objective", memory),
        ("Reliable recall takes priority", remember),
        ("Keep the transaction narrow only when", records),
        ("Expand beyond the index summary", contract),
    ):
        require(phrase in artifact, f"Memory priority guidance missing: {phrase}")


def validate_memory_audit_guidance() -> None:
    memory = read(ROOT / "skills" / "superb-skills" / "references" / "working-memory.md")
    remember = read(ROOT / "skills" / "remember-me" / "SKILL.md")
    records = read(ROOT / "skills" / "remember-me" / "references" / "record-management.md")
    research = read(ROOT / "skills" / "research-briefing" / "SKILL.md")
    audit_script = ROOT / "scripts" / "validate_memory_audit.py"
    require(audit_script.is_file(), "Missing deterministic memory audit validator")
    for phrase, artifact in (
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


def validate_instruction_design() -> None:
    root = ROOT / "skills" / "superb-skills"
    skill = read(root / "SKILL.md")
    instruction = read(root / "references" / "instruction-design.md")
    template = read(root / "references" / "project-instructions-template.md")
    checker = root / "scripts" / "check_instruction_length.py"
    require(len(skill) <= 6000, "superb-skills entrypoint exceeds the thin-router budget")
    require("research-scope checkpoint" not in skill, "superb-skills duplicates research procedure")
    require("remember-me/index.md" not in skill, "superb-skills duplicates memory retrieval procedure")
    require("8 KiB" not in skill, "superb-skills duplicates working-memory detail")
    for phrase in (
        "8,000-character limit",
        "7,600 characters",
        "Revise any artifact above the hard limit before delivery",
        "Do not copy the procedures of `research-briefing`, `remember-me`, `skill-creator`",
    ):
        require(phrase in instruction, f"Instruction artifact contract missing: {phrase}")
    require("omit unused headings" in template, "Project-instruction template is not selective")
    require(checker.is_file(), "Missing deterministic instruction-length checker")


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
        "instruction-hard-limit",
        "instruction-existing-skill-authority",
        "instruction-local-override",
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
        "teach-visual-digital-plan",
        "teach-visual-tool-only",
        "teach-visual-production-negative",
        "teach-visual-mixed-production-learning",
        "teach-visual-critique-learning",
        "teach-visual-critique-no-image",
        "teach-visual-material-art",
        "teach-visual-nonmaking",
        "teach-visual-calligraphy",
        "teach-visual-aid-boundary",
        "teach-visual-stylized-imagination",
        "teach-visual-cross-medium-transfer",
        "teach-visual-reference-study",
    ):
        require(case_id in ids, f"Missing required eval: {case_id}")
    results = json.loads(read(ROOT / "evals" / "results.json"))
    manifest = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))
    version_pattern = re.compile(r"^\d+\.\d+\.\d+$")
    results_version = results["plugin_version"]
    manifest_version = manifest["version"]
    require(version_pattern.fullmatch(results_version), "Invalid results version")
    require(version_pattern.fullmatch(manifest_version), "Invalid manifest version")
    require(
        tuple(map(int, results_version.split("."))) <= tuple(map(int, manifest_version.split("."))),
        "Results version cannot be newer than manifest version",
    )
    require(len(results["forward_tests"]) >= 4, "Missing forward-test results")


def validate_teach_me_routing() -> None:
    suite = json.loads(read(ROOT / "evals" / "teach-me-routing.json"))
    require(suite["suite"] == "teach-me-routing", "Unexpected teach-me routing suite")
    require(suite["version"] == "1.0.0", "Unexpected teach-me routing suite version")
    require(suite.get("purpose"), "Teach-me routing suite has no purpose")
    protocol = suite.get("fixture_protocol")
    require(isinstance(protocol, dict), "Teach-me routing fixture protocol is missing")
    require(set(protocol) == {"context", "turns", "expected_mode_by_turn"}, "Routing fixture protocol is incomplete")
    require(set(protocol["context"]) == {
        "project_instructions", "assistant_history", "tool_availability", "conversation_state",
    }, "Routing context protocol is incomplete")

    cases = suite["cases"]
    require(len(cases) >= 30, "Teach-me routing suite is too small")
    ids: set[str] = set()
    for case in cases:
        case_id = case.get("id")
        require(case_id and case_id not in ids, f"Duplicate or missing routing eval id: {case_id}")
        ids.add(case_id)
        turns = case.get("turns")
        require(isinstance(turns, list) and turns and all(isinstance(turn, str) and turn for turn in turns), f"{case_id} has invalid turns")
        require(case.get("input") == "\n\n".join(turns), f"{case_id} input does not mirror turns")
        context = case.get("context")
        require(isinstance(context, dict), f"{case_id} has no structured context")
        require(set(context) == {
            "project_instructions", "assistant_history", "tool_availability", "conversation_state",
        }, f"{case_id} context is incomplete")
        modes = case.get("expected_mode_by_turn")
        require(isinstance(modes, list) and len(modes) == len(turns), f"{case_id} mode expectations do not mirror turns")
        require(set(modes) <= {"DIRECT", "LEARNING", "AMBIGUOUS"}, f"{case_id} has invalid mode expectation")
        require(isinstance(case.get("expected_skills"), list), f"{case_id} missing expected_skills")
        for field in ("intended_behavior", "success_criteria", "failure_criteria"):
            require(case.get(field), f"{case_id} missing {field}")
    require(sum(len(case["turns"]) > 1 for case in cases) >= 12, "Too few multi-turn routing cases")
    for case_id in (
        "route-direct-factual-standalone", "route-explicit-understanding",
        "route-explicit-invocation-question-form", "route-explicit-direct-override",
        "route-active-lesson-ordinary-question", "route-active-local-explanation",
        "route-active-temporary-override", "route-active-permanent-exit",
        "route-active-source-request-concludes", "route-review-skill-negative",
        "route-ai-analysis-direct", "route-ai-exploration", "route-ambiguous-standalone",
        "route-ambiguous-active-lesson", "route-project-learning-default",
        "route-research-handoff-preserves-mode", "route-learning-plan-deliverable",
        "route-missing-reference-fallback", "route-ambiguous-mode-question",
        "route-active-missing-referent", "route-active-supporting-task-no-continuation",
        "route-active-unrelated-task", "route-active-return-after-unrelated",
        "route-direct-continuing-override", "route-explicit-direct-subscope-learning",
        "route-kahneman-critic-hypothesis",
    ):
        require(case_id in ids, f"Missing required teach-me routing eval: {case_id}")
    provenance = suite.get("provenance", {})
    require({"historical", "adapted", "synthetic"} <= set(provenance), "Routing suite provenance is incomplete")

    rubric = read(ROOT / "evals" / "teach-me-routing-scoring.md")
    for phrase in (
        "Activation and routing", "Mode continuity", "Learner reasoning", "Scaffold choice",
        "Evidence and uncertainty", "User control and stopping", "Critical", "Major",
        "Moderate", "Minor", "Critical failures and explicit mode-control failures are acceptance blockers",
        "Run the baseline before editing", "three independent trials",
        "Do not represent fixture presence as behavioral validation",
        "For a case marked **AMBIGUOUS**",
    ):
        require(phrase in rubric, f"Teach-me routing rubric missing: {phrase}")


def main() -> int:
    checks = (
        validate_manifest, validate_skills, validate_links,
        validate_contract, validate_remember_me, validate_record_backup, validate_teach_me, validate_memory_priorities,
        validate_memory_audit_guidance, validate_instruction_design, validate_evals,
        validate_teach_me_routing,
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
