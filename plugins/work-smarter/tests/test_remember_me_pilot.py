"""Evidence retention and treatment controls for actual CLI pilot runs."""
import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


PILOT = Path(__file__).resolve().parents[1] / 'evals/remember-me-benchmark/run_pilot.py'


def load():
    spec = importlib.util.spec_from_file_location('remember_me_pilot', PILOT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_usage_requires_completed_cli_event_and_preserves_missing_cache():
    pilot = load()
    events = [{'type': 'turn.completed', 'usage': {'input_tokens': 12, 'output_tokens': 3}}]
    assert pilot.cli_usage(events) == {
        'source': 'provider_reported', 'input_tokens': 12, 'output_tokens': 3,
    }
    assert pilot.cli_usage([{'type': 'item.completed', 'usage': events[0]['usage']}]) is None
    assert pilot.cli_usage([{'type': 'turn.completed', 'usage': {'input_tokens': True}}]) is None


def test_usage_sums_whole_turns_without_adding_cached_input_twice():
    pilot = load()
    events = [
        {'type': 'turn.completed', 'usage': {
            'input_tokens': 10, 'output_tokens': 4, 'cached_input_tokens': 2}},
        {'type': 'turn.completed', 'usage': {
            'input_tokens': 12, 'output_tokens': 6, 'cached_input_tokens': 11}},
    ]

    assert pilot.cli_usage(events) == {
        'source': 'provider_reported', 'input_tokens': 22,
        'output_tokens': 10, 'cached_input_tokens': 13,
    }
    assert pilot.cli_usage(events + [{'type': 'turn.completed'}]) is None


def test_treatments_require_index_and_assigned_navigation():
    pilot = load()
    event = lambda op, record='index': {'ok': True, 'op': op, 'record_id': record}
    assert pilot.treatment_valid('A', [event('read_full')])
    assert not pilot.treatment_valid('A', [event('read_full', 'topic-identity')])
    assert not pilot.treatment_valid('B', [event('read_section')])
    assert pilot.treatment_valid('C', [event('read_heading_map'), event('read_section')])
    assert not pilot.treatment_valid('D', [event('read_full')])
    assert not pilot.treatment_valid('C', [
        event('read_heading_map'), event('read_section'),
        event('read_full', 'topic-identity'),
    ])
    assert pilot.treatment_valid('C', [
        event('read_heading_map'), event('read_section'),
        event('read_heading_map', 'topic-identity'),
        event('read_full', 'topic-identity'),
    ])
    assert not pilot.treatment_valid('C', [
        event('read_heading_map'), event('read_section'),
        event('read_full', 'topic-identity'),
        event('read_heading_map', 'topic-identity'),
    ])
    assert pilot.treatment_valid('C', [
        event('read_heading_map'), event('read_section'),
        event('read_heading_map', 'topic-identity'),
        event('read_section', 'topic-identity'),
        event('read_full', 'topic-identity'),
    ])
    assert not pilot.treatment_valid('D', [
        event('read_heading_map'), event('read_section'),
        event('read_section', 'topic-identity'),
    ])
    assert pilot.treatment_valid('D', [
        event('read_heading_map'), event('read_section'),
        event('read_heading_map', 'topic-identity'),
        event('read_section', 'topic-identity'),
    ])


def test_prompt_has_task_instructions_without_answer_specific_labels(tmp_path):
    pilot = load()
    root = tmp_path / 'trial'
    pilot.load('adapter').initialize_trial(
        root, pilot.load('fixtures').build_trial('index-40k', 'C'))

    prompt = pilot.prompt_for(root)

    assert 'PUBLIC PACKET:' in prompt
    assert 'REMEMBER ME SKILL' in prompt
    assert 'uncertainty is none' not in prompt
    assert 'Attribution defaults' not in prompt
    assert 'synthetic source unless' not in prompt


def test_answer_schema_uses_candidate_chosen_labels_not_hidden_fact_ids():
    pilot = load()
    schema = pilot.answer_schema({'scenario_id': 'index-8k'})

    assert 'candidate-chosen descriptive label' in schema
    assert 'not a hidden gold fact ID' in schema
    assert 'matches facts by `authority_id` and `anchor`' in schema
    assert 'keyed by fact ID' not in schema


def test_protected_inventory_schema_does_not_request_controller_only_ids():
    pilot = load()
    schema = pilot.answer_schema({'scenario_id': 'amortized-update-audit'})

    assert 'protected_inventory' in schema
    assert 'controller-only item IDs' in schema
    assert 'matches items by' in schema
    assert '`id`' not in schema


def test_prompt_bundles_and_hashes_public_record_and_audit_instructions(tmp_path):
    pilot = load()
    root = tmp_path / 'trial'
    pilot.load('adapter').initialize_trial(
        root, pilot.load('fixtures').build_trial('closeout-sequence-40k', 'A'))

    prompt = pilot.prompt_for(root, phase='prepare')
    hashes = pilot.source_hashes()
    required = {
        'plugins/work-smarter/skills/remember-me/SKILL.md',
        'plugins/work-smarter/skills/remember-me/references/record-management.md',
        'plugins/work-smarter/skills/remember-me/references/transcript-sources.md',
        'plugins/work-smarter/skills/superb-skills/references/working-memory.md',
        'plugins/work-smarter/shared/handoff-contracts.md',
    }

    for relative in required:
        path = pilot.REPO_ROOT / relative
        assert relative in prompt
        assert path.read_text(encoding='utf-8') in prompt
        assert hashes[relative] == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize('exit_code,answer', [(7, '{}'), (0, 'invalid JSON')])
def test_failed_process_or_malformed_answer_cannot_pass_and_evidence_is_retained(
        tmp_path, exit_code, answer):
    pilot = load()
    executable = tmp_path / 'fake-codex'
    executable.write_text(
        '#!/usr/bin/env python3\nimport json, pathlib, sys\n'
        f'pathlib.Path(sys.argv[sys.argv.index("-o") + 1]).write_text({answer!r})\n'
        'print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 4, "output_tokens": 2}}))\n'
        'print("retained process diagnostic", file=sys.stderr)\n'
        f'sys.exit({exit_code})\n')
    executable.chmod(0o755)
    root = tmp_path / 'trial'
    result = pilot.run_trial(root, 'index-40k', 'A', codex=str(executable), timeout=10)
    assert result['status'] == 'failed'
    assert result['exit_code'] == exit_code
    assert result['served_model'] == 'unverified'
    assert result['unseen_holdout'] is False
    assert (root / 'cli-events.jsonl').read_text().strip()
    assert 'retained process diagnostic' in (root / 'stderr.txt').read_text()
    assert json.loads((root / 'result.json').read_text()) == result
    assert (root / 'controller/initial-state.json').is_file()
    assert (root / 'controller/final-state.json').is_file()


def test_resumed_turn_uses_supported_flags_and_original_trial_directory(tmp_path):
    pilot = load()
    executable = tmp_path / 'fake-codex'
    capture = tmp_path / 'captured-command.json'
    executable.write_text(
        '#!/usr/bin/env python3\nimport json, os, pathlib, sys\n'
        f"pathlib.Path({str(capture)!r}).write_text(json.dumps({{'argv': sys.argv[1:], 'cwd': os.getcwd()}}))\n"
        "output = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\n"
        "output.parent.mkdir(parents=True, exist_ok=True)\n"
        "output.write_text('{}')\n"
        "print(json.dumps({'type':'thread.started','thread_id':'session-42'}))\n"
        "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':3,'output_tokens':2}}))\n")
    executable.chmod(0o755)
    root = tmp_path / 'trial'
    agent_dir = root / 'agent'
    agent_dir.mkdir(parents=True)

    result = pilot.launch_turn(
        root, 'continue the exact session', codex=str(executable),
        resume_session_id='session-42', persistent_session=True, turn='resume')
    captured = json.loads(capture.read_text())

    assert result['exit_code'] == 0
    assert captured['argv'][:5] == [
        '--ask-for-approval', 'never', 'exec', 'resume', 'session-42']
    assert '-s' not in captured['argv']
    assert '-C' not in captured['argv']
    assert captured['cwd'] == str(agent_dir)


def test_launch_turn_terminates_and_reaps_process_group_on_interrupt(tmp_path, monkeypatch):
    pilot = load()

    class InterruptedProcess:
        pid = 12345
        returncode = None

        def __init__(self):
            self.calls = 0

        def communicate(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise KeyboardInterrupt
            self.returncode = -pilot.signal.SIGTERM
            return '', ''

    process = InterruptedProcess()
    signals = []
    monkeypatch.setattr(pilot.subprocess, 'Popen', lambda *args, **kwargs: process)
    monkeypatch.setattr(pilot.os, 'killpg', lambda pid, sig: signals.append((pid, sig)))
    root = tmp_path / 'trial'
    root.mkdir()

    with pytest.raises(KeyboardInterrupt):
        pilot.launch_turn(root, 'stop the interrupted turn')

    assert signals == [(process.pid, pilot.signal.SIGTERM)]
    assert process.calls == 2


def test_completed_run_without_usage_never_invents_token_counts():
    assert load().cli_usage([{'type': 'turn.completed'}]) is None


def test_tool_waits_for_other_process_and_returns_unique_receipts(tmp_path):
    fcntl = pytest.importorskip('fcntl')
    pilot = load()
    root = tmp_path / 'trial'
    pilot.load('adapter').initialize_trial(root, pilot.load('fixtures').build_trial('index-40k', 'C'))
    command = [sys.executable, str(PILOT), 'tool', '--root', str(root),
               '--request', '{"op":"read_heading_map","record_id":"index"}']
    with (root / 'controller/pilot-tool.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            with pytest.raises(subprocess.TimeoutExpired):
                process.communicate(timeout=0.3)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
            stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 0, stderr
    assert json.loads(stdout)['evidence']['event_seq'] == 1
    processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                 for _ in range(8)]
    receipts = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 0, stderr
        receipts.append(json.loads(stdout)['evidence']['event_seq'])
    assert sorted(receipts) == list(range(2, 10))
    trace = pilot.load('adapter').FixtureAdapter(root).trace
    assert [event['seq'] for event in trace] == list(range(1, 10))
