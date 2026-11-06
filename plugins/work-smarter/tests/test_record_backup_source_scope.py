import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "record-backup" / "scripts" / "check_source_scope.py"


def load_scope_checker():
    spec = importlib.util.spec_from_file_location("check_source_scope", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scope = load_scope_checker()


PROFILE = {
    "source_provider": "Synthetic Library",
    "source_container": "synthetic-library",
    "source_id": "backup-profile",
}
INDEX = {
    "source_provider": "Synthetic Library",
    "source_container": "synthetic-library",
    "source_id": "remember-me-index",
}
TECHNOLOGY = {
    "source_provider": "Synthetic Library",
    "source_container": "synthetic-library",
    "source_id": "technology-tools",
}
SALARY = {
    "source_provider": "Synthetic Drive",
    "source_container": "career-folder",
    "source_id": "salary-record",
}
TRANSCRIPT = {
    "source_provider": "Synthetic Drive",
    "source_container": "general-folder",
    "source_id": "troubleshooting-transcript",
}
ATTACHMENT = {
    "source_provider": "Synthetic Drive",
    "source_container": "career-folder",
    "source_id": "compensation-scan",
}


def packet(*, candidates, canonical=None, mentions=None, designations=None, excluded=None):
    if canonical is None:
        canonical = [
            {**INDEX, "owner": "remember-me", "evidence_reference": "verified-index"},
            {**TECHNOLOGY, "owner": "remember-me", "evidence_reference": "verified-index-topic"},
        ]
    return {
        "schema_version": 1,
        "profile": PROFILE,
        "canonical_records": canonical,
        "canonical_mentions": mentions or [],
        "user_designations": designations or [],
        "excluded": excluded or [],
        "candidates": candidates,
    }


def identity_key(identity):
    return tuple(identity[name] for name in scope.IDENTITY)


def selected_map(result):
    return {
        identity_key(row["identity"]): {
            entry["kind"] for entry in row["inclusion_basis"]
        }
        for row in result["selected"]
    }


def test_same_folder_and_topic_neighbor_is_outside_scope():
    result = scope.select_sources(packet(
        candidates=[
            {**PROFILE, "source_path": "settings/backup-profile.yaml"},
            {**INDEX, "source_path": "remember-me/index"},
            {**TECHNOLOGY, "source_path": "General/technology-tools.md"},
            {**TRANSCRIPT, "source_path": "General/Xfinity-troubleshooting.md"},
        ],
    ))

    selected = selected_map(result)
    assert identity_key(PROFILE) in selected
    assert identity_key(INDEX) in selected
    assert identity_key(TECHNOLOGY) in selected
    assert identity_key(TRANSCRIPT) not in selected
    assert result["complete"]
    assert [row["identity"] for row in result["outside_scope"]] == [TRANSCRIPT]


def test_canonical_mention_and_explicit_binary_designation_have_distinct_basis():
    result = scope.select_sources(packet(
        candidates=[
            {**PROFILE, "source_path": "settings/backup-profile.yaml"},
            {**INDEX, "source_path": "remember-me/index"},
            {**TECHNOLOGY, "source_path": "remember-me/technology-tools"},
            {**SALARY, "source_path": "career/salary-details.csv"},
            {**ATTACHMENT, "source_path": "career/compensation-scan.bin"},
        ],
        mentions=[{
            "from": TECHNOLOGY,
            "reference": "salary-details.csv",
            "state": "resolved",
            "targets": [SALARY],
        }],
        designations=[{
            **ATTACHMENT,
            "designation_reference": "user-designated-source-1",
        }],
    ))

    selected = selected_map(result)
    assert selected[identity_key(PROFILE)] == {"canonical-profile"}
    assert selected[identity_key(INDEX)] == {"canonical-record"}
    assert selected[identity_key(TECHNOLOGY)] == {"canonical-record"}
    assert selected[identity_key(SALARY)] == {"canonical-mention"}
    assert selected[identity_key(ATTACHMENT)] == {"user-designation"}
    technology = next(
        row for row in result["selected"]
        if identity_key(row["identity"]) == identity_key(TECHNOLOGY)
    )
    assert {
        "kind": "canonical-record",
        "owner": "remember-me",
        "reference": "verified-index-topic",
    } in technology["inclusion_basis"]
    assert result["complete"]


def test_supporting_file_links_do_not_expand_scope_even_for_user_designated_parent():
    other = {
        "source_provider": "Synthetic Drive",
        "source_container": "career-folder",
        "source_id": "unrelated-linked-file",
    }
    independently_designated = {
        "source_provider": "Synthetic Drive",
        "source_container": "career-folder",
        "source_id": "separately-designated-file",
    }
    result = scope.select_sources(packet(
        candidates=[PROFILE, INDEX, TECHNOLOGY, ATTACHMENT, other, independently_designated],
        mentions=[{
            "from": ATTACHMENT,
            "reference": "unrelated.md",
            "state": "resolved",
            "targets": [other],
        }],
        designations=[{
            **ATTACHMENT,
            "designation_reference": "user-designated-source-1",
        }, {
            **independently_designated,
            "designation_reference": "user-designated-source-2",
        }],
    ))

    selected = selected_map(result)
    assert identity_key(ATTACHMENT) in selected
    assert identity_key(other) not in selected
    assert selected[identity_key(independently_designated)] == {"user-designation"}
    assert result["complete"]


def test_duplicate_inventory_aliases_and_canonical_cycles_deduplicate():
    result = scope.select_sources(packet(
        candidates=[PROFILE, INDEX, TECHNOLOGY, TECHNOLOGY],
        canonical=[
            {**INDEX, "owner": "remember-me", "evidence_reference": "verified-index"},
            {**TECHNOLOGY, "owner": "remember-me", "evidence_reference": "verified-index-topic"},
        ],
        mentions=[
            {
                "from": INDEX,
                "reference": "technology-tools.md",
                "state": "resolved",
                "targets": [TECHNOLOGY],
            },
            {"from": TECHNOLOGY, "reference": "index.md", "state": "resolved", "targets": [INDEX]},
        ],
    ))

    selected = selected_map(result)
    assert len(result["selected"]) == 3
    assert selected[identity_key(INDEX)] == {"canonical-record", "canonical-mention"}
    assert selected[identity_key(TECHNOLOGY)] == {"canonical-record", "canonical-mention"}
    assert result["complete"]


@pytest.mark.parametrize(
    ("state", "targets", "expected_gap"),
    [
        ("ambiguous", [SALARY, ATTACHMENT], "ambiguous-reference"),
        ("inaccessible", [], "inaccessible-reference"),
        ("out-of-scope", [], "out-of-scope-reference"),
        ("resolved", [SALARY], "reference-outside-inventory"),
    ],
)
def test_unresolved_required_references_are_coverage_gaps(state, targets, expected_gap):
    candidates = [PROFILE, INDEX, TECHNOLOGY]
    result = scope.select_sources(packet(
        candidates=candidates,
        mentions=[{
            "from": TECHNOLOGY,
            "reference": "salary-details.csv",
            "state": state,
            "targets": targets,
        }],
    ))

    assert not result["complete"]
    assert any(gap["kind"] == expected_gap for gap in result["coverage_gaps"])
    assert identity_key(SALARY) not in selected_map(result)
    assert identity_key(TRANSCRIPT) not in selected_map(result)


def test_conflicting_resolutions_for_one_canonical_reference_are_not_selected():
    result = scope.select_sources(packet(
        candidates=[PROFILE, INDEX, TECHNOLOGY, SALARY, ATTACHMENT],
        mentions=[
            {
                "from": TECHNOLOGY,
                "reference": "salary.md",
                "state": "resolved",
                "targets": [SALARY],
            },
            {
                "from": TECHNOLOGY,
                "reference": "salary.md",
                "state": "resolved",
                "targets": [ATTACHMENT],
            },
        ],
    ))

    assert not result["complete"]
    assert any(gap["kind"] == "conflicting-reference-resolution" for gap in result["coverage_gaps"])
    selected = selected_map(result)
    assert identity_key(SALARY) not in selected
    assert identity_key(ATTACHMENT) not in selected


def test_excluded_required_reference_is_a_gap_but_unrelated_excluded_neighbor_is_not():
    result = scope.select_sources(packet(
        candidates=[PROFILE, INDEX, TECHNOLOGY, SALARY, TRANSCRIPT],
        mentions=[{
            "from": TECHNOLOGY,
            "reference": "salary.md",
            "state": "resolved",
            "targets": [SALARY],
        }],
        excluded=[SALARY, TRANSCRIPT],
    ))

    selected = selected_map(result)
    assert identity_key(SALARY) not in selected
    assert identity_key(TRANSCRIPT) not in selected
    assert any(gap["kind"] == "excluded-required-record" for gap in result["coverage_gaps"])


def test_cli_reports_a_valid_selection_and_returns_nonzero_for_coverage_gaps(tmp_path):
    complete_input = tmp_path / "complete.json"
    complete_input.write_text(json.dumps(packet(candidates=[PROFILE, INDEX, TECHNOLOGY])))
    complete = subprocess.run(
        [sys.executable, str(SCRIPT), str(complete_input)],
        capture_output=True,
        text=True,
    )

    assert complete.returncode == 0
    assert json.loads(complete.stdout)["complete"]

    incomplete_input = tmp_path / "incomplete.json"
    incomplete_input.write_text(json.dumps(packet(
        candidates=[PROFILE, INDEX, TECHNOLOGY],
        mentions=[{
            "from": TECHNOLOGY,
            "reference": "missing-source.md",
            "state": "inaccessible",
            "targets": [],
        }],
    )))
    incomplete = subprocess.run(
        [sys.executable, str(SCRIPT), str(incomplete_input)],
        capture_output=True,
        text=True,
    )

    assert incomplete.returncode == 1
    assert not json.loads(incomplete.stdout)["complete"]
