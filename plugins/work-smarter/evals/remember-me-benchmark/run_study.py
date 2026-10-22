"""Coordinate the bounded, two-turn synthetic Remember Me closeout sequence."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time


HERE = Path(__file__).resolve().parent
MAX_PROCESS_STARTS = 26
MAX_INFRASTRUCTURE_RECOVERY_STARTS = 2
RETRIEVAL_SCENARIOS = frozenset((
    'index-8k', 'index-40k', 'index-64k', 'topic-64k'))


def load(name):
    filename = 'run_pilot.py' if name == 'pilot' else f'{name}.py'
    spec = importlib.util.spec_from_file_location(f'study_{name}', HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _manifest():
    return load('fixtures').load_manifest()


def _atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(f'.{path.name}.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n',
                         encoding='utf-8')
    temporary.replace(path)


def _locked_ledger(study_root):
    import fcntl

    study_root = Path(study_root)
    study_root.mkdir(parents=True, exist_ok=True)
    lock_path = study_root / 'launch-ledger.lock'
    lock = lock_path.open('a+', encoding='utf-8')
    fcntl.flock(lock, fcntl.LOCK_EX)
    ledger_path = study_root / 'launch-ledger.json'
    try:
        ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        manifest = _manifest()
        budget = manifest.get('closeout_launch_budget', {})
        ledger = {
            'schema_version': 1,
            'maximum_process_starts': budget.get(
                'maximum_additional_process_starts', MAX_PROCESS_STARTS),
            'maximum_infrastructure_recovery_starts': budget.get(
                'maximum_infrastructure_recovery_starts',
                MAX_INFRASTRUCTURE_RECOVERY_STARTS),
            'behavioral_retries': budget.get('behavioral_retries', False),
            'launches': [],
        }
        _atomic_json(ledger_path, ledger)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
        raise ValueError('the launch ledger is unreadable') from error
    if (not isinstance(ledger, dict) or ledger.get('schema_version') != 1
            or not isinstance(ledger.get('launches'), list)
            or ledger.get('maximum_process_starts') != MAX_PROCESS_STARTS
            or ledger.get('maximum_infrastructure_recovery_starts')
            != MAX_INFRASTRUCTURE_RECOVERY_STARTS
            or ledger.get('behavioral_retries') is not False):
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
        raise ValueError('the launch ledger does not match the closeout budget')
    return lock, ledger_path, ledger


def reserve_launch(study_root, trial_id, turn, *, attempt_kind='behavioral',
                   recovery_for=None, recovery_reason=None):
    """Charge one process start before launching; repeated trial turns are refused."""
    import fcntl

    if attempt_kind not in ('behavioral', 'infrastructure_recovery'):
        raise ValueError('unknown process-start attempt kind')
    if attempt_kind == 'infrastructure_recovery':
        if not recovery_for or not recovery_reason:
            raise ValueError('infrastructure recovery requires a target and reason')
    elif recovery_for is not None or recovery_reason is not None:
        raise ValueError('behavioral launches cannot claim infrastructure recovery')

    lock, ledger_path, ledger = _locked_ledger(study_root)
    try:
        launches = ledger['launches']
        if len(launches) >= MAX_PROCESS_STARTS:
            raise ValueError('closeout process-start budget of 26 is exhausted')
        if any(item.get('trial_id') == trial_id and item.get('turn') == turn
               for item in launches):
            raise ValueError('this trial turn already has a charged launch')
        recoveries = [item for item in launches
                      if item.get('attempt_kind') == 'infrastructure_recovery']
        if attempt_kind == 'infrastructure_recovery':
            if len(recoveries) >= MAX_INFRASTRUCTURE_RECOVERY_STARTS:
                raise ValueError('infrastructure recovery allowance of 2 is exhausted')
            if any(item.get('recovery_for') == recovery_for for item in recoveries):
                raise ValueError('this trial already used its infrastructure recovery')
        sequence = len(launches) + 1
        launch = {
            'sequence': sequence, 'trial_id': trial_id, 'turn': turn,
            'status': 'reserved', 'process_started': None,
            'attempt_kind': attempt_kind,
        }
        if attempt_kind == 'infrastructure_recovery':
            launch.update({
                'recovery_for': recovery_for,
                'recovery_reason': recovery_reason,
            })
        launches.append(launch)
        _atomic_json(ledger_path, ledger)
        return sequence
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def complete_launch(study_root, sequence, process):
    """Record the observed result of a charged process start."""
    import fcntl

    lock, ledger_path, ledger = _locked_ledger(study_root)
    try:
        launch = next((item for item in ledger['launches']
                       if item.get('sequence') == sequence), None)
        if launch is None or launch.get('status') != 'reserved':
            raise ValueError('launch ledger entry is missing or already completed')
        launch['status'] = 'completed'
        process_started = process.get('process_started')
        launch['process_started'] = (
            process_started if isinstance(process_started, bool) else None)
        launch['exit_code'] = process.get('exit_code')
        launch['session_id'] = process.get('session_id')
        launch['errors'] = list(process.get('errors', []))
        _atomic_json(ledger_path, ledger)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def _failed_launch(error):
    detail = f'{type(error).__name__}: {error}'
    return {
        'events': [], 'errors': [f'runner exception: {detail}'],
        'exit_code': None, 'elapsed_seconds': None, 'argv': [],
        'session_id': None, 'answer_path': None, 'process_started': None,
    }


def run_retrieval_trial(study_root, *, scenario, candidate, codex='codex',
                        model='gpt-6-luna', effort='high',
                        sandbox='danger-full-access', timeout=240):
    """Run and ledger one allowed single-turn retrieval cell exactly once."""
    if scenario not in RETRIEVAL_SCENARIOS:
        raise ValueError('scenario is outside the bounded retrieval panel')
    if candidate not in ('A', 'B', 'C', 'D'):
        raise ValueError('candidate must be one of A, B, C or D')
    study_root = Path(study_root).resolve()
    trial_id = f'{scenario}-{candidate}'
    root = study_root / trial_id
    if root.exists():
        raise FileExistsError('Use a fresh study root for every behavioral trial')

    sequence = reserve_launch(study_root, trial_id, 'single')
    pilot = load('pilot')
    try:
        result = pilot.run_trial(
            root, scenario, candidate, codex=codex, model=model,
            effort=effort, sandbox=sandbox, timeout=timeout)
    except Exception as error:
        complete_launch(study_root, sequence, {
            'process_started': None, 'exit_code': None,
            'session_id': None, 'errors': [f'runner exception: {error}'],
        })
        raise

    complete_launch(study_root, sequence, {
        'process_started': result.get('process_started'),
        'exit_code': result.get('exit_code'),
        'session_id': result.get('session_id'),
        'errors': result.get('errors', []),
    })
    ledger = json.loads((study_root / 'launch-ledger.json').read_text(encoding='utf-8'))
    result = dict(result)
    result.update({
        'launch_ledger_sequence': sequence,
        'launches_used': len(ledger['launches']),
        'launch_budget_maximum': MAX_PROCESS_STARTS,
    })
    _atomic_json(root / 'result.json', result)
    return result


def validate_staged_candidate(bundle, adapter):
    """Independently check the exact staged bytes before scripted approval."""
    errors = []
    control = adapter.controller_control
    authorization = control.get('maintenance_authorization')
    authorized = isinstance(authorization, dict)
    authorization = authorization if authorized else {}
    stage_path = adapter.controller_root / 'staged-index.json'
    try:
        staged = json.loads(stage_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, ['no readable staged candidate']
    if not authorized:
        errors.append('the fixture does not authorize index maintenance')
    if not isinstance(staged, dict):
        return None, ['the staged candidate is not an object']
    content = staged.get('candidate_content')
    if not isinstance(content, str) or not content.strip():
        errors.append('the staged candidate has no content')
        content = ''
    candidate_bytes = content.encode('utf-8')
    candidate_sha256 = hashlib.sha256(candidate_bytes).hexdigest()
    initial_index = bundle['records'].get('index', {})
    if len(candidate_bytes) >= len(initial_index.get('content', '').encode('utf-8')):
        errors.append('the staged candidate is not shorter than the source index')
    if bundle['gold'].get('maintenance_trigger', {}).get('audit_due') is not True:
        errors.append('the controller trigger does not authorize maintenance')
    if (staged.get('record_id') != 'index'
            or staged.get('expected_version') != authorization.get('expected_version')
            or staged.get('candidate_sha256') != candidate_sha256
            or staged.get('candidate_bytes') != len(candidate_bytes)):
        errors.append('staged candidate identity, version or digest does not match')
    adapter_module = load('adapter')
    if staged.get('stage_id') != adapter_module.maintenance_stage_id(
            'index', staged.get('expected_version'), candidate_sha256):
        errors.append('staged candidate ID is not bound to its digest and version')

    required_targets = set(bundle['gold'].get('pointer_targets', []))
    required_bindings = {
        f"{item.get('authority_id')}#{item.get('anchor')}"
        for item in bundle['gold'].get('protected_inventory', [])
        if isinstance(item, dict)
    }
    missing_targets = sorted(target for target in required_targets if target not in content)
    missing_bindings = sorted(binding for binding in required_bindings if binding not in content)
    if missing_targets:
        errors.append('staged candidate lost pointer targets: ' + ', '.join(missing_targets))
    if missing_bindings:
        errors.append('staged candidate lost pointer bindings: ' + ', '.join(missing_bindings))

    update = bundle['gold'].get('update_authorization')
    save_attempts = [event for event in adapter.trace
                     if event.get('op') == 'save_append']
    if not isinstance(update, dict) or len(save_attempts) != 1:
        errors.append('the exact authorized topic append must occur once before approval')
    else:
        save = save_attempts[0]
        expected_request = {
            'op': 'save_append', 'record_id': update.get('record_id'),
            'expected_version': update.get('expected_version'),
            'append_text': update.get('append_text'),
        }
        saved_content = (bundle['records'].get(update.get('record_id'), {}).get('content', '')
                         + update.get('append_text', ''))
        save_response = save.get('response')
        save_response = save_response if isinstance(save_response, dict) else {}
        readback = next((event for event in adapter.trace
                         if event.get('seq', 0) > save.get('seq', 0)
                         and event.get('op') == 'read_full' and event.get('ok')
                         and event.get('record_id') == update.get('record_id')
                         and event.get('record_version') == update.get('new_version')
                         and event.get('response', {}).get('version') == update.get('new_version')
                         and event.get('response', {}).get('content') == saved_content
                         and event.get('response', {}).get('content_sha256')
                         == hashlib.sha256(saved_content.encode('utf-8')).hexdigest()), None)
        if (not save.get('ok') or save.get('request') != expected_request
                or save.get('pre_write_version') != update.get('expected_version')
                or save.get('post_write_version') != update.get('new_version')
                or save_response.get('version') != update.get('new_version')
                or save_response.get('content_sha256')
                != hashlib.sha256(saved_content.encode('utf-8')).hexdigest()
                or readback is None):
            errors.append('the exact authorized topic append lacks independent readback')

    for fact in bundle['gold'].get('protected_inventory', []):
        record = adapter.state.get(fact.get('authority_id'))
        if (not isinstance(record, dict)
                or fact.get('value') not in record.get('content', '')
                or fact.get('anchor') not in {
                    heading['anchor'] for heading in adapter_module.headings_for(
                        record.get('content', ''))
                }):
            errors.append(f"protected authority is unavailable: {fact.get('id')}")
    for record_id, initial in bundle['records'].items():
        if record_id == 'index':
            continue
        expected = dict(initial)
        update = bundle['gold'].get('update_authorization')
        if isinstance(update, dict) and record_id == update.get('record_id'):
            expected['content'] += update['append_text']
            expected['version'] = update['new_version']
        if adapter.state.get(record_id) != expected:
            errors.append(f'authoritative or unrelated record changed: {record_id}')

    successful_stages = [event for event in adapter.trace
                         if event.get('op') == 'stage_index_maintenance' and event.get('ok')]
    if len(successful_stages) != 1:
        errors.append('exactly one successful stage receipt is required')
    elif successful_stages[0].get('response') != {
            'ok': True, 'stage_id': staged.get('stage_id'), 'record_id': 'index',
            'expected_version': staged.get('expected_version'),
            'candidate_sha256': candidate_sha256,
            'candidate_bytes': len(candidate_bytes), 'candidate_content': content}:
        errors.append('the stage receipt does not bind the persisted candidate bytes')
    if adapter.state.get('index') != bundle['records'].get('index'):
        errors.append('canonical index changed before controller approval')
    return staged, errors


def _continuation_prompt(public, staged, approval, rejection_reasons):
    if approval is not None and approval.get('approved') is True:
        decision = (
            'The controller approved this exact staged candidate. Call '
            '`promote_index_maintenance` using the following payload values, then read the '
            'promoted index back and finish the full task answer. Do not alter any value.\n'
            f"record_id: {approval['record_id']}\n"
            f"expected_version: {approval['expected_version']}\n"
            f"stage_id: {approval['stage_id']}\n"
            f"candidate_sha256: {approval['candidate_sha256']}\n"
            f"approval_id: {approval['approval_id']}\n"
        )
    else:
        reasons = '; '.join(rejection_reasons) or 'no valid staged candidate was presented'
        decision = (
            'The controller declined maintenance approval after its independent review: '
            f'{reasons}. Do not promote or attempt another write. Finish by reporting the '
            'verified facts and the incomplete maintenance outcome from the trace.\n'
        )
    return f'''Continue the same synthetic Remember Me task and exact session. The public packet
and prior receipts are still the task context. This is the controller decision after reviewing
the staged candidate {staged.get('stage_id') if staged else '(none)'}.

{decision}
{load('pilot').answer_schema(public)}

Use only the adapter command and the public packet. This local Full Access run has procedural
instructions only: controller files and host resources remain accessible to shell commands.
Do not inspect those files or services. Behavioral failures are retained; do not retry them.
'''


def run_closeout_sequence(study_root, *, scenario='closeout-sequence-40k', candidate='C',
                          codex='codex', model='gpt-6-luna', effort='high',
                          sandbox='danger-full-access', timeout=240):
    if scenario != 'closeout-sequence-40k':
        raise ValueError('run_study only coordinates closeout-sequence-40k')
    fixtures, adapter_module, scorer = (
        load(name) for name in ('fixtures', 'adapter', 'score'))
    bundle = fixtures.build_trial(scenario, candidate, trigger_threshold_kib=32)
    study_root = Path(study_root).resolve()
    study_root.mkdir(parents=True, exist_ok=True)
    trial_id = f'{scenario}-{candidate}'
    root = study_root / trial_id
    if root.exists():
        raise FileExistsError('Use a fresh study root for every behavioral trial')
    root.mkdir()
    adapter_module.initialize_trial(root, bundle)
    pilot = load('pilot')
    public = bundle['public']
    prepare_prompt = pilot.prompt_for(root, phase='prepare')
    (root / 'prompt-prepare.txt').write_text(prepare_prompt, encoding='utf-8')
    started = time.perf_counter()
    launch_sequence = reserve_launch(study_root, trial_id, 'prepare')
    cancellation = None
    try:
        prepare = pilot.launch_turn(
            root, prepare_prompt, codex=codex, model=model, effort=effort,
            sandbox=sandbox, timeout=timeout, turn='prepare', persistent_session=True)
    except KeyboardInterrupt as error:
        prepare = _failed_launch(error)
        cancellation = error
    except Exception as error:
        prepare = _failed_launch(error)
    complete_launch(study_root, launch_sequence, prepare)
    errors = list(prepare['errors'])
    approval = None
    staged = None
    stage_errors = []
    continue_session = (
        not errors and prepare.get('process_started')
        and prepare.get('session_id')
        and any(event.get('type') == 'turn.completed' for event in prepare['events']))
    if continue_session:
        observed = adapter_module.FixtureAdapter(root)
        staged, stage_errors = validate_staged_candidate(bundle, observed)
        if staged is not None and not stage_errors:
            approval_id = 'closeout-' + staged['candidate_sha256'][:16]
            approval = adapter_module.authorize_index_maintenance(
                root, stage_id=staged['stage_id'],
                candidate_sha256=staged['candidate_sha256'],
                approval_id=approval_id, approved=True)
        elif staged is not None:
            try:
                adapter_module.authorize_index_maintenance(
                    root, stage_id=staged['stage_id'],
                    candidate_sha256=staged['candidate_sha256'],
                    approval_id='closeout-declined-' + staged['candidate_sha256'][:12],
                    approved=False)
            except (ValueError, OSError) as error:
                stage_errors.append(f'controller could not record the decline: {error}')
        continuation_prompt = _continuation_prompt(
            public, staged, approval, stage_errors)
        (root / 'prompt-resume.txt').write_text(continuation_prompt, encoding='utf-8')
        continuation_sequence = reserve_launch(study_root, trial_id, 'resume')
        try:
            resumed = pilot.launch_turn(
                root, continuation_prompt, codex=codex, model=model, effort=effort,
                sandbox=sandbox, timeout=timeout, turn='resume',
                resume_session_id=prepare['session_id'], persistent_session=True)
        except KeyboardInterrupt as error:
            resumed = _failed_launch(error)
            cancellation = error
        except Exception as error:
            resumed = _failed_launch(error)
        complete_launch(study_root, continuation_sequence, resumed)
        errors.extend(resumed['errors'])
        if resumed.get('session_id') not in (None, prepare['session_id']):
            errors.append('continuation did not retain the exact session ID')
    else:
        resumed = None
        errors.append('preparation did not provide a completed resumable session')
    errors.extend(stage_errors)

    answer = None
    if resumed is not None:
        answer_path = resumed.get('answer_path')
        if answer_path is None:
            errors.append('continuation did not produce an answer file')
        else:
            try:
                answer = json.loads(Path(answer_path).read_text(encoding='utf-8'))
                if not isinstance(answer, dict):
                    raise ValueError('answer must be a JSON object')
            except (ValueError, OSError, TypeError) as error:
                errors.append(f'invalid final answer after continuation: {error}')
    score = None
    treatment = False
    all_events = list(prepare['events']) + (list(resumed['events']) if resumed else [])
    try:
        observed = adapter_module.FixtureAdapter(root)
        final = observed.snapshot()
        treatment = pilot.treatment_valid(candidate, observed.trace)
        score = scorer.score_trial(
            public=bundle['public'], gold=bundle['gold'],
            reference_records=final, initial_records=bundle['records'],
            trace=observed.trace, answer=answer, usage=pilot.cli_usage(all_events),
            maintenance_approval=approval)
    except (ValueError, OSError, TypeError, KeyError) as error:
        errors.append(f'controller scoring failed: {error}')
    hashes = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(root.rglob('*')) if path.is_file()}
    elapsed = time.perf_counter() - started
    ledger = json.loads((study_root / 'launch-ledger.json').read_text(encoding='utf-8'))
    result = {
        'schema_version': 1,
        'evidence_kind': 'exposed-synthetic-development-closeout-sequence',
        'scenario': scenario, 'candidate': candidate,
        'status': 'passed' if (not errors and treatment and isinstance(score, dict)
                               and score.get('status') == 'passed') else 'failed',
        'requested_model': model, 'served_model': 'unverified', 'requested_effort': effort,
        'sandbox': sandbox,
        'isolation': 'procedural; controller files and host resources accessible to shell',
        'unseen_holdout': False, 'exit_codes': [prepare['exit_code']] + (
            [resumed['exit_code']] if resumed else []),
        'session_id': prepare.get('session_id'), 'errors': errors,
        'treatment_valid': treatment, 'end_to_end_seconds': elapsed,
        'usage_source': 'retained Codex CLI turn.completed events across both turns',
        'launches_used': len(ledger['launches']),
        'launch_budget_maximum': MAX_PROCESS_STARTS,
        'score': score, 'approval': approval,
        'candidate_review': {'stage_id': staged.get('stage_id') if staged else None,
                             'candidate_sha256': staged.get('candidate_sha256') if staged else None,
                             'accepted': bool(approval and approval.get('approved')),
                             'errors': stage_errors},
        'commands': [prepare['argv']] + ([resumed['argv']] if resumed else []),
        'fixture_identity': bundle['fixture_identity'], 'gold_identity': bundle['gold_identity'],
        'source_hashes': pilot.source_hashes(),
        'raw_evidence_sha256': hashes,
    }
    _atomic_json(root / 'result.json', result)
    if cancellation is not None:
        raise cancellation
    return result


def recover_closeout_resume(study_root, *, trial_id):
    """Complete only A's existing session after the known unsupported-flag failure."""
    expected_trial = 'closeout-sequence-40k-A'
    if trial_id != expected_trial:
        raise ValueError('only the preserved closeout A CLI failure is recoverable')
    study_root = Path(study_root).resolve()
    root = study_root / trial_id
    result_path = root / 'result.json'
    recovered_path = root / 'recovered-result.json'
    if not result_path.is_file():
        raise ValueError('the original trial result is missing')
    if recovered_path.exists():
        raise FileExistsError('a recovery result already exists for this trial')

    original_bytes = result_path.read_bytes()
    original = json.loads(original_bytes)
    if (original.get('scenario') != 'closeout-sequence-40k'
            or original.get('candidate') != 'A'
            or original.get('exit_codes') != [0, 2]
            or original.get('status') != 'failed'):
        raise ValueError('the original result does not match the recoverable A attempt')
    session_id = original.get('session_id')
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError('the original trial has no resumable session ID')
    stderr_path = root / 'stderr-resume.txt'
    events_path = root / 'cli-events-resume.jsonl'
    prompt_path = root / 'prompt-resume.txt'
    if not all(path.is_file() for path in (stderr_path, events_path, prompt_path)):
        raise ValueError('the original continuation evidence is incomplete')
    if "unexpected argument '-s' found" not in stderr_path.read_text(encoding='utf-8'):
        raise ValueError('the continuation failure is not the confirmed unsupported -s flag')
    prior_events = []
    for line in events_path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            event = json.loads(line)
            if isinstance(event, dict):
                prior_events.append(event)
    if any(event.get('type') == 'turn.completed' for event in prior_events):
        raise ValueError('the original continuation completed; it cannot be retried')
    ledger_path = study_root / 'launch-ledger.json'
    ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
    prior_launches = [entry for entry in ledger.get('launches', [])
                      if entry.get('trial_id') == trial_id]
    if ([entry.get('turn') for entry in prior_launches] != ['prepare', 'resume']
            or any(entry.get('status') != 'completed' for entry in prior_launches)):
        raise ValueError('the launch ledger does not show exactly one failed continuation')

    pilot = load('pilot')
    fixtures, adapter_module, scorer = (
        load(name) for name in ('fixtures', 'adapter', 'score'))
    bundle = fixtures.build_trial(
        'closeout-sequence-40k', 'A', trigger_threshold_kib=32)
    prepare_events = []
    prepare_events_path = root / 'cli-events-prepare.jsonl'
    for line in prepare_events_path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            event = json.loads(line)
            if isinstance(event, dict):
                prepare_events.append(event)
    if pilot.cli_session_id(prepare_events) != session_id:
        raise ValueError('the preparation output does not match the recorded session')

    recovery_sequence = reserve_launch(
        study_root, trial_id, 'resume-recovery-1',
        attempt_kind='infrastructure_recovery', recovery_for=trial_id,
        recovery_reason='Codex CLI exec resume rejected the unsupported -s flag')
    recovery_prompt = prompt_path.read_text(encoding='utf-8')
    try:
        recovered = pilot.launch_turn(
            root, recovery_prompt, model=original.get('requested_model', 'gpt-6-luna'),
            effort=original.get('requested_effort', 'high'),
            sandbox=original.get('sandbox', 'danger-full-access'),
            turn='resume-recovery-1', resume_session_id=session_id,
            persistent_session=True)
    except Exception as error:
        recovered = {
            'events': [], 'errors': [f'recovery runner exception: {error}'],
            'exit_code': None, 'elapsed_seconds': 0, 'argv': [],
            'session_id': None, 'process_started': None,
        }
    complete_launch(study_root, recovery_sequence, recovered)

    errors = list(recovered.get('errors', []))
    if recovered.get('session_id') not in (None, session_id):
        errors.append('recovery did not retain the exact original session ID')
    recovery_turn_completed = any(
        event.get('type') == 'turn.completed' for event in recovered.get('events', []))
    answer = None
    answer_path = recovered.get('answer_path')
    if answer_path is not None:
        try:
            answer = json.loads(Path(answer_path).read_text(encoding='utf-8'))
            if not isinstance(answer, dict):
                raise ValueError('answer must be a JSON object')
        except (ValueError, OSError) as error:
            errors.append(f'invalid recovered answer: {error}')
    approval = None
    staged = None
    stage_errors = []
    score = None
    treatment = False
    try:
        observed = adapter_module.FixtureAdapter(root)
        staged, stage_errors = validate_staged_candidate(bundle, observed)
        approval = observed.controller_control.get('maintenance_approval')
        treatment = pilot.treatment_valid('A', observed.trace)
        all_events = (prepare_events + prior_events + list(recovered.get('events', [])))
        score = scorer.score_trial(
            public=bundle['public'], gold=bundle['gold'],
            reference_records=observed.snapshot(), initial_records=bundle['records'],
            trace=observed.trace, answer=answer,
            usage=pilot.cli_usage(all_events), maintenance_approval=approval)
    except (ValueError, OSError, TypeError, KeyError) as error:
        errors.append(f'controller scoring failed: {error}')
    errors.extend(stage_errors)
    ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
    raw_hashes = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*')) if path.is_file()
        and path.name not in ('result.json', 'recovered-result.json')
    }
    recovery_completed = bool(
        recovered.get('process_started') is True
        and recovered.get('exit_code') == 0 and recovery_turn_completed
        and recovered.get('session_id') in (None, session_id))
    result = {
        'schema_version': 1,
        'evidence_kind': 'exposed-synthetic-development-closeout-sequence',
        'scenario': 'closeout-sequence-40k', 'candidate': 'A',
        'status': 'passed' if (original.get('status') != 'failed'
                               and not errors and treatment
                               and isinstance(score, dict)
                               and score.get('status') == 'passed') else 'failed',
        'requested_model': original.get('requested_model'),
        'served_model': original.get('served_model', 'unverified'),
        'requested_effort': original.get('requested_effort'),
        'sandbox': original.get('sandbox'), 'isolation': original.get('isolation'),
        'unseen_holdout': False, 'session_id': session_id,
        'prior_behavioral_status': original.get('status'),
        'prior_errors': original.get('errors', []),
        'errors': errors, 'treatment_valid': treatment,
        'recovery': {
            'completed': recovery_completed,
            'turn_completed': recovery_turn_completed,
            'exit_code': recovered.get('exit_code'),
            'session_id': recovered.get('session_id'),
            'launch_ledger_sequence': recovery_sequence,
            'original_result_sha256': hashlib.sha256(original_bytes).hexdigest(),
            'reason': 'The original same-session continuation did not start because '
                      'Codex CLI rejected the unsupported -s resume flag.',
        },
        'exit_codes': original.get('exit_codes', []) + [recovered.get('exit_code')],
        'launches_used': len(ledger['launches']),
        'launch_budget_maximum': MAX_PROCESS_STARTS,
        'infrastructure_recoveries_used': sum(
            entry.get('attempt_kind') == 'infrastructure_recovery'
            for entry in ledger['launches']),
        'infrastructure_recovery_budget_maximum': MAX_INFRASTRUCTURE_RECOVERY_STARTS,
        'score': score,
        'approval': approval,
        'candidate_review': {
            'stage_id': staged.get('stage_id') if staged else None,
            'candidate_sha256': staged.get('candidate_sha256') if staged else None,
            'accepted': bool(approval and approval.get('approved')),
            'errors': stage_errors,
        },
        'commands': original.get('commands', []) + [recovered.get('argv', [])],
        'fixture_identity': bundle['fixture_identity'],
        'gold_identity': bundle['gold_identity'],
        'original_source_hashes': original.get('source_hashes', {}),
        'recovery_source_hashes': pilot.source_hashes(),
        'raw_evidence_sha256': raw_hashes,
    }
    _atomic_json(recovered_path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('run', 'recover'))
    parser.add_argument('--root', type=Path, required=True,
                        help='fresh study root shared by every closeout launch')
    parser.add_argument('--trial-id', default='closeout-sequence-40k-A')
    parser.add_argument('--scenario', default='closeout-sequence-40k')
    parser.add_argument('--candidate', choices=('A', 'B', 'C', 'D'), default='C')
    parser.add_argument('--sandbox', choices=('read-only', 'danger-full-access'),
                        default='danger-full-access')
    parser.add_argument('--model', default='gpt-6-luna')
    parser.add_argument('--effort', default='high')
    parser.add_argument('--timeout', type=int, default=240)
    args = parser.parse_args()
    if args.action == 'recover':
        result = recover_closeout_resume(args.root, trial_id=args.trial_id)
    elif args.scenario == 'closeout-sequence-40k':
        result = run_closeout_sequence(
            args.root, scenario=args.scenario, candidate=args.candidate,
            model=args.model, effort=args.effort, sandbox=args.sandbox,
            timeout=args.timeout)
    else:
        result = run_retrieval_trial(
            args.root, scenario=args.scenario, candidate=args.candidate,
            model=args.model, effort=args.effort, sandbox=args.sandbox,
            timeout=args.timeout)
    print(json.dumps({key: result.get(key) for key in (
        'status', 'scenario', 'errors', 'end_to_end_seconds', 'launches_used',
        'recovery')}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
