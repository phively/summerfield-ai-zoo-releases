"""Run exposed synthetic development trials; never label them sealed acceptance."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
INSTRUCTION_FILES = (
    Path('plugins/work-smarter/skills/remember-me/SKILL.md'),
    Path('plugins/work-smarter/skills/remember-me/references/record-management.md'),
    Path('plugins/work-smarter/skills/remember-me/references/transcript-sources.md'),
    Path('plugins/work-smarter/skills/superb-skills/references/working-memory.md'),
    Path('plugins/work-smarter/shared/handoff-contracts.md'),
)
SOURCE_FILES = (
    Path('run_pilot.py'), Path('run_study.py'), Path('fixtures.py'),
    Path('adapter.py'), Path('score.py'), Path('manifest.json'),
)


def source_hashes():
    paths = {str(relative): REPO_ROOT / relative for relative in INSTRUCTION_FILES}
    code_root = Path('plugins/work-smarter/evals/remember-me-benchmark')
    paths.update({str(code_root / name): HERE / name for name in SOURCE_FILES
                  if (HERE / name).is_file()})
    return {relative: hashlib.sha256(path.read_bytes()).hexdigest()
            for relative, path in sorted(paths.items())}


def instruction_bundle():
    sections = []
    for relative in INSTRUCTION_FILES:
        path = REPO_ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        sections.append(f'### {relative.as_posix()} (sha256: {digest})\n'
                        f'{path.read_text(encoding="utf-8")}')
    return '\n\n'.join(sections)


def load(name):
    spec = importlib.util.spec_from_file_location(f'pilot_{name}', HERE / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_locked_tool(root, request):
    import fcntl

    with (root / 'controller/pilot-tool.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        adapter = load('adapter').FixtureAdapter(root)
        result = adapter.call(json.loads(request))
        event = adapter.trace[-1]
        print(json.dumps({
            'result': result,
            'evidence': {
                'event_seq': event['seq'], 'response_sha256': event['response_sha256'],
                'record_id': event['record_id'], 'version': event['record_version'],
            },
        }))


def cli_usage(events):
    completed = [event for event in events if event.get('type') == 'turn.completed']
    if not completed:
        return None
    usage_rows = [event.get('usage') for event in completed]
    if any(not isinstance(usage, dict) for usage in usage_rows):
        return None
    result = {}
    for key in ('input_tokens', 'output_tokens', 'cached_input_tokens'):
        values = [usage.get(key) for usage in usage_rows]
        if all(type(value) is int and value >= 0 for value in values):
            # Cached input is already included in input_tokens.
            result[key] = sum(values)
    return {'source': 'provider_reported', **result} if result else None


def treatment_valid(candidate, trace):
    reads = [(position, event) for position, event in enumerate(trace, 1)
             if event.get('ok') and event.get('op') in (
                 'read_full', 'read_heading_map', 'read_section')]
    if not any(event.get('record_id') == 'index' for _, event in reads):
        return False
    operations = {event.get('op') for _, event in reads}
    if candidate in ('A', 'B'):
        return not operations.intersection({'read_heading_map', 'read_section'})
    index_operations = {event.get('op') for _, event in reads
                        if event.get('record_id') == 'index'}
    if not {'read_heading_map', 'read_section'} <= index_operations:
        return False

    records_with_prior_heading_map = set()
    index_section_after_map = False
    for _, event in reads:
        record_id = event.get('record_id')
        operation = event.get('op')
        if operation == 'read_heading_map':
            records_with_prior_heading_map.add(record_id)
        elif operation in ('read_full', 'read_section'):
            if record_id not in records_with_prior_heading_map:
                return False
            if record_id == 'index' and operation == 'read_section':
                index_section_after_map = True
    return index_section_after_map


def answer_schema(public):
    schema = '''Return only a JSON object with a `facts` object. Give each item a
candidate-chosen descriptive label; the label is not a hidden gold fact ID. Each fact
contains `value`, `attribution`, `uncertainty`, `authority_id`, `anchor`, and `evidence`.
Each evidence item contains `event_seq`, `record_id`, `anchor`, `version`, and
`response_sha256`. Cite only adapter receipts from successful reads. The controller
matches facts by `authority_id` and `anchor`, not by the descriptive label.'''
    if 'staged_review_policy' in public:
        schema += ''' Add `audit_review` with `candidate_record_id`, `disposition`,
`lost_items`, `unresolved_pointers`, `recovered_pointers`, `review_due`,
`write_authorized`, `maintenance_action`, and `evidence` containing the candidate
read's `event_seq` and `response_sha256`.'''
    if public.get('scenario_id') in (
            'amortized-update-audit', 'closeout-sequence-40k'):
        schema += ''' Add a `protected_inventory` array. Each item includes `value`,
`authority_id`, `anchor`, `attribution`, `uncertainty`, and trace-backed `evidence`.
Do not include controller-only item IDs; the controller matches items by
`authority_id` and `anchor`.'''
    return schema


def prompt_for(root, *, phase='single'):
    tool = shlex.join([sys.executable, str(HERE / 'run_pilot.py'), 'tool',
                       '--root', str(root)])
    public = (root / 'agent/public.json').read_text(encoding='utf-8')
    packet = json.loads(public)
    instructions = f'''Execute this synthetic Remember Me development task using the public instructions below.
Use only the supplied public packet and the adapter command. Do not read controller
files, repository source/tests, other records, credentials, or external services.
This restriction is procedural, not an enforced filesystem boundary. Do not edit files.
Complete the public task and follow its task sequence and retrieval instruction.
Call tools through: {tool} --request '<JSON object with op and arguments>'
Each call returns result plus an evidence receipt. Use that receipt in citations.
Read operations are read_full(record_id), read_heading_map(record_id), and
read_section(record_id, anchor). Use only tool operations advertised in the public
packet. Never manufacture a trace or receipt. If execution is denied, do not retry;
report the failure.
{answer_schema(packet)}

PUBLIC PACKET:
{public}

REMEMBER ME SKILL AND PUBLIC RECORD/AUDIT REFERENCES (synthetic adapter replaces live Library tools for this task):
{instruction_bundle()}
'''
    if phase == 'prepare':
        return instructions + '''

This is the preparation turn of a two-turn maintenance task. Complete the supplied
read, save, readback and audit steps, then stage the shorter candidate only if the
public trigger is due. Stop after the stage receipt. Do not promote the candidate
or invent an approval; the controller will continue this exact session with its
decision. Your response after staging may be a short JSON status object.
'''
    if phase != 'single':
        raise ValueError(f'unsupported prompt phase: {phase}')
    return instructions


def cli_session_id(events):
    for event in events:
        if event.get('type') == 'thread.started':
            session_id = event.get('thread_id') or event.get('session_id')
            if isinstance(session_id, str) and session_id.strip():
                return session_id
    return None


def _terminate_process_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()


def launch_turn(root, prompt, *, codex='codex', model='gpt-6-luna', effort='high',
                sandbox='danger-full-access', timeout=240, turn='trial',
                resume_session_id=None, persistent_session=False):
    root = Path(root).resolve()
    if turn == 'trial':
        events_path, stderr_path, answer_path = (
            root / 'cli-events.jsonl', root / 'stderr.txt', root / 'answer.json')
    else:
        events_path, stderr_path, answer_path = (
            root / f'cli-events-{turn}.jsonl', root / f'stderr-{turn}.txt',
            root / f'answer-{turn}.json')
    argv = [codex, '--ask-for-approval', 'never', 'exec']
    if resume_session_id:
        argv.extend(['resume', resume_session_id])
    argv.extend(['--ignore-user-config', '--skip-git-repo-check', '--json', '-m', model,
                 '-c', f'model_reasoning_effort="{effort}"', '-c',
                 'project_doc_max_bytes=0', '--disable', 'apps', '--disable', 'plugins',
                 '--disable', 'hooks', '--disable', 'multi_agent', '--disable', 'fast_mode'])
    if not persistent_session:
        argv.append('--ephemeral')
    process_cwd = None
    if resume_session_id:
        # `exec resume` inherits the persisted session sandbox and has no -s/-C
        # flags. Match the original session's working directory for lookup.
        process_cwd = root / 'agent'
    else:
        argv.extend(['-s', sandbox, '-C', str(root / 'agent')])
    argv.extend(['-o', str(answer_path), '-'])
    errors = []
    started = time.perf_counter()
    exit_code = None
    process_started = False
    with events_path.open('w', encoding='utf-8') as stdout, stderr_path.open(
            'w', encoding='utf-8') as stderr:
        try:
            process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=stdout,
                                       stderr=stderr, text=True, start_new_session=True,
                                       cwd=process_cwd)
            process_started = True
            try:
                process.communicate(prompt, timeout=timeout)
            except subprocess.TimeoutExpired:
                errors.append('model process timed out')
                _terminate_process_group(process)
            except BaseException:
                _terminate_process_group(process)
                raise
            exit_code = process.returncode
        except OSError as error:
            errors.append(f'model launch failed: {error}')
    elapsed = time.perf_counter() - started
    events = []
    for line in events_path.read_text(encoding='utf-8').splitlines():
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError('event must be an object')
            events.append(event)
        except ValueError as error:
            errors.append(f'invalid CLI event: {error}')
    if exit_code != 0:
        errors.append(f'model process exit status: {exit_code}')
    if not any(event.get('type') == 'turn.completed' for event in events):
        errors.append('no completed model turn')
    if any(event.get('type') in ('turn.failed', 'error') for event in events):
        errors.append('CLI reported a failed turn or error')
    return {
        'events': events, 'errors': errors, 'exit_code': exit_code,
        'elapsed_seconds': elapsed, 'argv': argv,
        'session_id': cli_session_id(events), 'answer_path': answer_path,
        'events_path': events_path, 'stderr_path': stderr_path,
        'process_started': process_started,
    }


def run_trial(root, scenario='index-40k', candidate='C', *, codex='codex',
              model='gpt-6-luna', effort='high', sandbox='danger-full-access',
              timeout=240):
    root = Path(root).resolve()
    fixtures, adapter, scorer = (load(name) for name in ('fixtures', 'adapter', 'score'))
    bundle = fixtures.build_trial(scenario, candidate)
    if bundle['gold'].get('maintenance_authorization'):
        raise ValueError('maintenance scenarios require the run_study coordinator')
    adapter.initialize_trial(root, bundle)
    prompt = prompt_for(root)
    (root / 'prompt.txt').write_text(prompt, encoding='utf-8')
    process = launch_turn(
        root, prompt, codex=codex, model=model, effort=effort, sandbox=sandbox,
        timeout=timeout)
    errors = list(process['errors'])
    answer = None
    try:
        answer = json.loads(process['answer_path'].read_text(encoding='utf-8'))
        if not isinstance(answer, dict):
            raise ValueError('answer must be a JSON object')
    except (ValueError, OSError) as error:
        errors.append(f'invalid final answer: {error}')
    score = None
    treatment = False
    try:
        observed = adapter.FixtureAdapter(root)
        final = observed.snapshot()
        treatment = treatment_valid(candidate, observed.trace)
        score = scorer.score_trial(
            public=bundle['public'], gold=bundle['gold'],
            reference_records=final, initial_records=bundle['records'],
            trace=observed.trace, answer=answer, usage=cli_usage(process['events']))
    except (ValueError, OSError, TypeError, KeyError) as error:
        errors.append(f'controller scoring failed: {error}')
    hashes = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(root.rglob('*')) if path.is_file()}
    result = {
        'schema_version': 1, 'evidence_kind': 'exposed-synthetic-development-pilot',
        'scenario': scenario, 'candidate': candidate,
        'status': 'passed' if (not errors and treatment and isinstance(score, dict)
                               and score.get('status') == 'passed') else 'failed',
        'requested_model': model, 'served_model': 'unverified', 'requested_effort': effort,
        'sandbox': sandbox, 'isolation': 'procedural; controller files accessible to shell',
        'unseen_holdout': False, 'exit_code': process['exit_code'],
        'process_started': process['process_started'], 'session_id': process['session_id'],
        'errors': errors,
        'treatment_valid': treatment, 'end_to_end_seconds': process['elapsed_seconds'],
        'usage_source': 'retained Codex CLI turn.completed events',
        'score': score, 'command': process['argv'],
        'fixture_identity': bundle['fixture_identity'], 'gold_identity': bundle['gold_identity'],
        'source_hashes': source_hashes(),
        'raw_evidence_sha256': hashes,
    }
    (root / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('trial', 'tool'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--request')
    parser.add_argument('--scenario', default='index-40k')
    parser.add_argument('--candidate', choices=('A', 'B', 'C', 'D'), default='C')
    parser.add_argument('--sandbox', choices=('read-only', 'danger-full-access'),
                        default='danger-full-access')
    parser.add_argument('--model', default='gpt-6-luna')
    parser.add_argument('--effort', default='high')
    parser.add_argument('--timeout', type=int, default=240)
    args = parser.parse_args()
    if args.action == 'tool':
        if not args.request:
            parser.error('tool requires --request')
        run_locked_tool(args.root, args.request)
    else:
        result = run_trial(args.root, args.scenario, args.candidate, model=args.model,
                           effort=args.effort, sandbox=args.sandbox, timeout=args.timeout)
        print(json.dumps({key: result[key] for key in ('status', 'errors', 'end_to_end_seconds')}))
        return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
