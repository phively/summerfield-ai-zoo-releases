"""Focused deterministic controls for the two-turn closeout coordinator."""
import importlib.util
import json
from pathlib import Path

import pytest


STUDY = (Path(__file__).resolve().parents[1]
         / 'evals/remember-me-benchmark/run_study.py')


def load_study():
    spec = importlib.util.spec_from_file_location('remember_me_study', STUDY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _answer(bundle, adapter, save_sequence):
    facts = {}
    inventory = []
    for fact in bundle['gold']['required_facts']:
        matching = [event for event in adapter.trace
                    if event['seq'] > save_sequence and event['ok']
                    and event['op'] in ('read_full', 'read_section')
                    and event['record_id'] == fact['authority_id']
                    and fact['value'] in event['response'].get('content', '')]
        assert matching
        event = matching[-1]
        citation = {
            'event_seq': event['seq'], 'record_id': event['record_id'],
            'anchor': fact['anchor'], 'version': event['record_version'],
            'response_sha256': event['response_sha256'],
        }
        facts[fact['id']] = {
            key: fact[key] for key in (
                'value', 'attribution', 'uncertainty', 'authority_id', 'anchor')
        }
        facts[fact['id']]['evidence'] = [citation]
        inventory.append({
            key: fact[key] for key in (
                'id', 'value', 'authority_id', 'anchor', 'attribution', 'uncertainty')
        })
        inventory[-1]['evidence'] = [citation]
    return {'facts': facts, 'protected_inventory': inventory}


def _read_sources(adapter, gold):
    for fact in gold['required_facts']:
        adapter.read_heading_map(fact['authority_id'])
        adapter.read_section(fact['authority_id'], fact['anchor'])


def _modules(study, monkeypatch):
    modules = {name: study.load(name) for name in (
        'pilot', 'fixtures', 'adapter', 'score')}
    original_load = study.load
    monkeypatch.setattr(study, 'load', lambda name: (
        modules[name] if name in modules else original_load(name)))
    return modules


def _launch_script(study, modules, monkeypatch, *, stage_content=None):
    pilot, fixtures, adapter_module = (
        modules['pilot'], modules['fixtures'], modules['adapter'])
    observed_calls = []

    def fake_launch(root, prompt, **options):
        root = Path(root)
        observed_calls.append(dict(options))
        adapter = adapter_module.FixtureAdapter(root)
        bundle = fixtures.build_trial(
            'closeout-sequence-40k', 'C', trigger_threshold_kib=32)
        if options.get('resume_session_id') is None:
            adapter.read_heading_map('index')
            adapter.read_section('index', 'routing-and-ownership')
            _read_sources(adapter, bundle['gold'])
            update = bundle['gold']['update_authorization']
            adapter.call({
                'op': 'save_append', 'record_id': update['record_id'],
                'expected_version': update['expected_version'],
                'append_text': update['append_text'],
            })
            save_event = adapter.trace[-1]
            adapter.read_full(update['record_id'])
            _read_sources(adapter, bundle['gold'])
            content = stage_content or fixtures._index_text(False)
            adapter.call({
                'op': 'stage_index_maintenance', 'record_id': 'index',
                'expected_version': 'synthetic-v1', 'candidate_content': content,
            })
            Path(root, 'answer-prepare.json').write_text(
                json.dumps({'prepared': True}), encoding='utf-8')
            return {
                'events': [
                    {'type': 'thread.started', 'thread_id': 'fixture-session-42'},
                    {'type': 'turn.completed', 'usage': {
                        'input_tokens': 100, 'output_tokens': 40,
                        'cached_input_tokens': 80}},
                ],
                'errors': [], 'exit_code': 0, 'elapsed_seconds': 0.01,
                'argv': ['fake-codex', 'exec'], 'session_id': 'fixture-session-42',
                'answer_path': Path(root, 'answer-prepare.json'),
                'process_started': True,
            }

        assert options.get('resume_session_id') == 'fixture-session-42'
        approval = adapter.controller_control.get('maintenance_approval')
        if approval and approval.get('approved'):
            adapter.call({
                'op': 'promote_index_maintenance', 'record_id': 'index',
                'expected_version': approval['expected_version'],
                'stage_id': approval['stage_id'],
                'candidate_sha256': approval['candidate_sha256'],
                'approval_id': approval['approval_id'],
            })
            adapter.read_full('index')
        save_sequence = next(event['seq'] for event in adapter.trace
                             if event.get('op') == 'save_append' and event.get('ok'))
        answer = _answer(bundle, adapter, save_sequence)
        answer_path = Path(root, 'answer-resume.json')
        answer_path.write_text(json.dumps(answer), encoding='utf-8')
        return {
            'events': [{'type': 'turn.completed', 'usage': {
                'input_tokens': 120, 'output_tokens': 30,
                'cached_input_tokens': 100}}],
            'errors': [], 'exit_code': 0, 'elapsed_seconds': 0.01,
            'argv': ['fake-codex', 'exec', 'resume', 'fixture-session-42'],
            'session_id': None, 'answer_path': answer_path,
            'process_started': True,
        }

    monkeypatch.setattr(pilot, 'launch_turn', fake_launch)
    return observed_calls


def test_closeout_uses_exact_session_and_charges_both_turns(tmp_path, monkeypatch):
    study = load_study()
    modules = _modules(study, monkeypatch)
    calls = _launch_script(study, modules, monkeypatch)

    result = study.run_closeout_sequence(tmp_path / 'study')

    assert result['status'] == 'passed', result['score']['checks']
    assert len(calls) == 2
    assert calls[0]['persistent_session'] is True
    assert calls[0].get('resume_session_id') is None
    assert calls[1]['resume_session_id'] == 'fixture-session-42'
    assert result['score']['measurements']['token_usage']['actual_total_tokens'] == 290
    assert result['score']['measurements']['token_usage']['cached_input_tokens'] == 180
    assert result['launches_used'] == 2
    assert 'procedural' in result['isolation']
    assert not any('--ephemeral' in argv for argv in result['commands'])


@pytest.mark.parametrize('failed_turn', ('prepare', 'resume'))
def test_closeout_launch_exception_completes_ledger_and_writes_failure(
        failed_turn, tmp_path, monkeypatch):
    study = load_study()
    modules = _modules(study, monkeypatch)
    pilot = modules['pilot']
    _launch_script(study, modules, monkeypatch)
    working_launch = pilot.launch_turn

    def launch_with_exception(root, prompt, **options):
        if options['turn'] == failed_turn:
            raise RuntimeError(f'{failed_turn} failed before returning a result')
        return working_launch(root, prompt, **options)

    monkeypatch.setattr(pilot, 'launch_turn', launch_with_exception)
    study_root = tmp_path / 'study'

    result = study.run_closeout_sequence(study_root)

    ledger = json.loads((study_root / 'launch-ledger.json').read_text())
    trial_root = study_root / 'closeout-sequence-40k-C'
    failed_launch = next(item for item in ledger['launches']
                         if item['turn'] == failed_turn)
    assert result['status'] == 'failed'
    assert 'runner exception' in failed_launch['errors'][0]
    assert failed_launch['status'] == 'completed'
    assert failed_launch['process_started'] is None
    assert all(item['status'] == 'completed' for item in ledger['launches'])
    assert (trial_root / 'result.json').is_file()
    assert json.loads((trial_root / 'result.json').read_text())['status'] == 'failed'


def test_closeout_interrupt_writes_failure_before_propagating(tmp_path, monkeypatch):
    study = load_study()
    modules = _modules(study, monkeypatch)
    pilot = modules['pilot']
    _launch_script(study, modules, monkeypatch)

    def interrupted_launch(root, prompt, **options):
        raise KeyboardInterrupt

    monkeypatch.setattr(pilot, 'launch_turn', interrupted_launch)
    study_root = tmp_path / 'study'

    with pytest.raises(KeyboardInterrupt):
        study.run_closeout_sequence(study_root)

    ledger = json.loads((study_root / 'launch-ledger.json').read_text())
    trial_root = study_root / 'closeout-sequence-40k-C'
    assert ledger['launches'][0]['status'] == 'completed'
    assert ledger['launches'][0]['process_started'] is None
    assert 'KeyboardInterrupt' in ledger['launches'][0]['errors'][0]
    result = json.loads((trial_root / 'result.json').read_text())
    assert result['status'] == 'failed'
    assert result['exit_codes'] == [None]


def test_invalid_staged_candidate_is_declined_without_promotion(tmp_path, monkeypatch):
    study = load_study()
    modules = _modules(study, monkeypatch)
    calls = _launch_script(
        study, modules, monkeypatch, stage_content='# missing protected routes\n')

    result = study.run_closeout_sequence(tmp_path / 'study')

    assert result['status'] == 'failed'
    assert result['candidate_review']['accepted'] is False
    assert result['candidate_review']['errors']
    assert calls[1]['resume_session_id'] == 'fixture-session-42'
    assert not any(event['op'] == 'promote_index_maintenance'
                   for event in modules['adapter'].FixtureAdapter(
                       tmp_path / 'study' / 'closeout-sequence-40k-C').trace)


def test_controller_requires_topic_append_readback_before_stage_approval(tmp_path):
    study = load_study()
    fixtures = study.load('fixtures')
    adapter_module = study.load('adapter')
    bundle = fixtures.build_trial(
        'closeout-sequence-40k', 'C', trigger_threshold_kib=32)
    root = tmp_path / 'trial'
    adapter_module.initialize_trial(root, bundle)
    adapter = adapter_module.FixtureAdapter(root)
    update = bundle['gold']['update_authorization']
    assert adapter.call({
        'op': 'save_append', 'record_id': update['record_id'],
        'expected_version': update['expected_version'],
        'append_text': update['append_text'],
    })['ok']
    assert adapter.call({
        'op': 'stage_index_maintenance', 'record_id': 'index',
        'expected_version': 'synthetic-v1',
        'candidate_content': fixtures._index_text(False),
    })['ok']

    staged, errors = study.validate_staged_candidate(bundle, adapter)

    assert staged
    assert 'the exact authorized topic append lacks independent readback' in errors


def test_unsupported_scenario_and_reused_trial_fail_before_a_new_launch(
        tmp_path, monkeypatch):
    study = load_study()
    modules = _modules(study, monkeypatch)
    calls = _launch_script(study, modules, monkeypatch)
    root = tmp_path / 'study'

    with pytest.raises(ValueError, match='only coordinates'):
        study.run_closeout_sequence(root, scenario='index-40k')
    assert calls == []
    study.run_closeout_sequence(root)
    with pytest.raises(FileExistsError, match='fresh study root'):
        study.run_closeout_sequence(root)
    assert len(calls) == 2


def test_launch_budget_caps_initial_and_resumed_process_starts(tmp_path):
    study = load_study()
    root = tmp_path / 'study'

    for sequence in range(study.MAX_PROCESS_STARTS):
        charged = study.reserve_launch(root, f'trial-{sequence}', 'prepare')
        assert charged == sequence + 1
        study.complete_launch(root, charged, {
            'process_started': True, 'exit_code': 0, 'session_id': None, 'errors': [],
        })

    with pytest.raises(ValueError, match='budget of 26'):
        study.reserve_launch(root, 'trial-27', 'prepare')


def test_launch_ledger_keeps_process_start_unknown_when_runner_raises(tmp_path):
    study = load_study()
    root = tmp_path / 'study'
    sequence = study.reserve_launch(root, 'index-8k-A', 'single')

    study.complete_launch(root, sequence, {
        'process_started': None, 'exit_code': None,
        'session_id': None, 'errors': ['runner exception'],
    })

    ledger = json.loads((root / 'launch-ledger.json').read_text())
    assert ledger['launches'][0]['status'] == 'completed'
    assert ledger['launches'][0]['process_started'] is None


def test_resume_recovery_continues_same_session_and_preserves_first_result(
        tmp_path, monkeypatch):
    study = load_study()
    modules = _modules(study, monkeypatch)
    pilot, fixtures = modules['pilot'], modules['fixtures']
    launch_calls = []

    def failed_resume_launch(root, prompt, **options):
        launch_calls.append(dict(options))
        if options['turn'] == 'prepare':
            return {
                'events': [
                    {'type': 'thread.started', 'thread_id': 'fixture-session-recovery'},
                    {'type': 'turn.completed', 'usage': {
                        'input_tokens': 20, 'output_tokens': 10}},
                ],
                'errors': [], 'exit_code': 0, 'elapsed_seconds': 0.01,
                'argv': ['fake-codex', 'exec'], 'session_id': 'fixture-session-recovery',
                'answer_path': Path(root, 'answer-prepare.json'),
                'process_started': True,
            }
        return {
            'events': [], 'errors': ['model process exit status: 2'],
            'exit_code': 2, 'elapsed_seconds': 0.01,
            'argv': ['fake-codex', 'exec', 'resume'],
            'session_id': None, 'answer_path': Path(root, 'answer-resume.json'),
            'process_started': True,
        }

    monkeypatch.setattr(pilot, 'launch_turn', failed_resume_launch)
    study_root = tmp_path / 'study'
    study.run_closeout_sequence(study_root, candidate='A')
    trial_root = study_root / 'closeout-sequence-40k-A'
    (trial_root / 'cli-events-prepare.jsonl').write_text(
        '{"type":"thread.started","thread_id":"fixture-session-recovery"}\n'
        '{"type":"turn.completed","usage":{"input_tokens":20,"output_tokens":10}}\n',
        encoding='utf-8')
    (trial_root / 'cli-events-resume.jsonl').write_text('', encoding='utf-8')
    (trial_root / 'stderr-resume.txt').write_text(
        "error: unexpected argument '-s' found\n", encoding='utf-8')
    original_result = (trial_root / 'result.json').read_bytes()
    recovery_calls = []

    def recovered_launch(root, prompt, **options):
        recovery_calls.append(dict(options))
        answer_path = Path(root, 'answer-resume-recovery-1.json')
        answer_path.write_text(json.dumps({'facts': {}}), encoding='utf-8')
        return {
            'events': [{'type': 'turn.completed', 'usage': {
                'input_tokens': 15, 'output_tokens': 8}}],
            'errors': [], 'exit_code': 0, 'elapsed_seconds': 0.01,
            'argv': ['fake-codex', 'exec', 'resume', 'fixture-session-recovery'],
            'session_id': 'fixture-session-recovery', 'answer_path': answer_path,
            'process_started': True,
        }

    monkeypatch.setattr(pilot, 'launch_turn', recovered_launch)
    result = study.recover_closeout_resume(study_root, trial_id='closeout-sequence-40k-A')

    assert result['recovery']['completed'] is True
    assert recovery_calls[0]['resume_session_id'] == 'fixture-session-recovery'
    assert recovery_calls[0]['turn'] == 'resume-recovery-1'
    assert (trial_root / 'result.json').read_bytes() == original_result
    assert (trial_root / 'recovered-result.json').is_file()
    ledger = json.loads((study_root / 'launch-ledger.json').read_text())
    assert len(ledger['launches']) == 3
    assert ledger['launches'][2]['attempt_kind'] == 'infrastructure_recovery'
    assert ledger['launches'][2]['recovery_for'] == 'closeout-sequence-40k-A'


def test_launch_ledger_caps_infrastructure_recovery_starts(tmp_path):
    study = load_study()
    root = tmp_path / 'study'

    for number in (1, 2):
        sequence = study.reserve_launch(
            root, f'trial-{number}', f'recovery-{number}',
            attempt_kind='infrastructure_recovery',
            recovery_for=f'original-{number}', recovery_reason='confirmed CLI error')
        study.complete_launch(root, sequence, {
            'process_started': True, 'exit_code': 0,
            'session_id': None, 'errors': [],
        })

    with pytest.raises(ValueError, match='infrastructure recovery allowance'):
        study.reserve_launch(
            root, 'trial-3', 'recovery-3',
            attempt_kind='infrastructure_recovery',
            recovery_for='original-3', recovery_reason='confirmed CLI error')


def test_retrieval_trials_share_the_launch_ledger_and_cannot_repeat(tmp_path, monkeypatch):
    study = load_study()
    modules = _modules(study, monkeypatch)
    calls = []

    def fake_trial(root, scenario, candidate, **options):
        root = Path(root)
        calls.append((root, scenario, candidate, options))
        root.mkdir(parents=True)
        return {
            'status': 'passed', 'errors': [], 'exit_code': 0,
            'process_started': True, 'session_id': None,
        }

    monkeypatch.setattr(modules['pilot'], 'run_trial', fake_trial)
    study_root = tmp_path / 'study'

    result = study.run_retrieval_trial(
        study_root, scenario='index-8k', candidate='A')

    assert result['status'] == 'passed'
    assert result['launch_budget_maximum'] == 26
    assert result['launches_used'] == 1
    assert result['launch_ledger_sequence'] == 1
    assert len(calls) == 1
    ledger = json.loads((study_root / 'launch-ledger.json').read_text())
    assert ledger['launches'][0]['trial_id'] == 'index-8k-A'
    assert ledger['launches'][0]['turn'] == 'single'
    assert ledger['launches'][0]['process_started'] is True

    with pytest.raises(FileExistsError, match='fresh study root'):
        study.run_retrieval_trial(
            study_root, scenario='index-8k', candidate='A')
    assert len(calls) == 1
