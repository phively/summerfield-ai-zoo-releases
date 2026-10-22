"""Synthetic record adapter with byte-accurate, append-only traces."""
import copy
import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path


SAVE_OP = 'save_append'
STAGE_MAINTENANCE_OP = 'stage_index_maintenance'
PROMOTE_MAINTENANCE_OP = 'promote_index_maintenance'


def canonical_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def maintenance_stage_id(record_id, expected_version, candidate_sha256):
    return 'index-maintenance-' + sha256_bytes(canonical_json({
        'record_id': record_id,
        'expected_version': expected_version,
        'candidate_sha256': candidate_sha256,
    }).encode('utf-8'))[:16]


def _staged_candidate_is_valid(staged, authorization):
    if not isinstance(authorization, dict) or not isinstance(staged, dict):
        return False
    content = staged.get('candidate_content')
    if not isinstance(content, str):
        return False
    content_bytes = content.encode('utf-8')
    candidate_sha256 = sha256_bytes(content_bytes)
    expected_version = staged.get('expected_version')
    return (
        staged.get('record_id') == authorization.get('record_id')
        and expected_version == authorization.get('expected_version')
        and staged.get('candidate_sha256') == candidate_sha256
        and staged.get('candidate_bytes') == len(content_bytes)
        and staged.get('stage_id') == maintenance_stage_id(
            'index', expected_version, candidate_sha256)
    )


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n',
                          encoding='utf-8')


def write_json_atomic(path, value):
    path = Path(path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=path.parent,
                prefix=f'.{path.name}.', suffix='.tmp', delete=False) as stream:
            temporary_path = Path(stream.name)
            stream.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _slug(title):
    slug = re.sub(r'[^\w\- ]', '', title.lower(), flags=re.UNICODE)
    slug = re.sub(r'[\s_]+', '-', slug).strip('-')
    return slug or 'section'


def headings_for(content):
    """Return actual Markdown headings and exact UTF-8 section ranges."""
    raw = content.encode('utf-8')
    headings = []
    offset = 0
    counts = {}
    for line in content.splitlines(keepends=True):
        match = re.match(r'^(#{1,6})[ \t]+(.+?)\s*#*[ \t]*(?:\r?\n)?$', line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            base = _slug(title)
            occurrence = counts.get(base, 0)
            counts[base] = occurrence + 1
            anchor = base if occurrence == 0 else f'{base}-{occurrence}'
            headings.append({
                'level': level, 'title': title, 'anchor': anchor,
                'start_byte': offset,
            })
        offset += len(line.encode('utf-8'))

    for index, heading in enumerate(headings):
        end = len(raw)
        for following in headings[index + 1:]:
            if following['level'] <= heading['level']:
                end = following['start_byte']
                break
        heading['end_byte'] = end
    return headings


def initialize_trial(root, trial):
    """Create a fresh controller directory; only public.json is agent-facing."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise FileExistsError('Use a unique empty benchmark trial directory')
    agent_root = root / 'agent'
    controller_root = root / 'controller'
    agent_root.mkdir()
    controller_root.mkdir()
    write_json(agent_root / 'public.json', trial['public'])
    write_json(controller_root / 'control.json', {
        'scenario_id': trial['public']['scenario_id'],
        'candidate': trial['candidate'],
        'fixture_identity': trial['fixture_identity'],
        'gold_identity': trial['gold_identity'],
        'calibration_digest': trial['calibration_digest'],
        'gold': trial['gold'],
        'update_authorization': copy.deepcopy(
            trial['gold'].get('update_authorization')),
        'maintenance_authorization': copy.deepcopy(
            trial['gold'].get('maintenance_authorization')),
        'maintenance_approval': None,
    })
    write_json(controller_root / 'initial-state.json', trial['records'])
    write_json(controller_root / 'state.json', trial['records'])
    write_json(controller_root / 'receipt.json', {
        'scenario_id': trial['public']['scenario_id'],
        'candidate': trial['candidate'],
        'fixture_identity': trial['fixture_identity'],
        'gold_identity': trial['gold_identity'],
        'recovery_state_sha256': trial['gold'].get('recovery_state_sha256'),
        'evidence_kind': 'deterministic-control',
    })
    (controller_root / 'events.jsonl').write_text('', encoding='utf-8')


class FixtureAdapter:
    def __init__(self, root):
        self.root = Path(root)
        self.agent_root = self.root / 'agent'
        self.controller_root = self.root / 'controller'
        self.public_data = json.loads((self.agent_root / 'public.json').read_text(encoding='utf-8'))
        self.controller_control = json.loads(
            (self.controller_root / 'control.json').read_text(encoding='utf-8'))
        self.initial_state = json.loads(
            (self.controller_root / 'initial-state.json').read_text(encoding='utf-8'))
        self.state = json.loads((self.controller_root / 'state.json').read_text(encoding='utf-8'))
        events_path = self.controller_root / 'events.jsonl'
        self.trace = ([json.loads(line) for line in events_path.read_text(encoding='utf-8').splitlines()]
                      if events_path.exists() else [])

    def public(self):
        return copy.deepcopy(self.public_data)

    def _record(self, op, request, response, ok, started_ns, record=None,
                error=None, content_bytes=0, request_bytes=None, write_bytes=0,
                pre_write_version=None, post_write_version=None):
        finished_ns = time.perf_counter_ns()
        response_bytes = canonical_json(response).encode('utf-8') if ok else b''
        event = {
            'seq': len(self.trace) + 1,
            'op': op,
            'request': copy.deepcopy(request),
            'ok': bool(ok),
            'record_id': record['id'] if record else request.get('record_id'),
            'record_version': record.get('version') if record else None,
            'elapsed_ns': max(0, finished_ns - started_ns),
            'content_bytes': int(content_bytes) if ok else 0,
            'request_bytes': (len(canonical_json(request).encode('utf-8'))
                              if request_bytes is None else int(request_bytes)),
            'write_bytes': int(write_bytes) if ok else 0,
            'returned_bytes': len(response_bytes),
            'response_sha256': sha256_bytes(response_bytes) if ok else None,
            'response': copy.deepcopy(response) if ok else None,
        }
        if op in (SAVE_OP, PROMOTE_MAINTENANCE_OP):
            event['pre_write_version'] = pre_write_version
            event['post_write_version'] = post_write_version
        if error:
            event['error'] = error
        self.trace.append(event)
        with (self.controller_root / 'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + '\n')
        return copy.deepcopy(response)

    def read_full(self, record_id, reason='candidate'):
        started = time.perf_counter_ns()
        record = self.state.get(record_id)
        if record is None:
            return self._record('read_full', {'record_id': record_id, 'reason': reason},
                                None, False, started, error='unknown synthetic record')
        response = {
            'record_id': record['id'], 'path': record['path'],
            'version': record['version'], 'kind': record['kind'],
            'content': record['content'],
            'content_sha256': sha256_bytes(record['content'].encode('utf-8')),
            'reason': reason,
        }
        if 'last_verified_audit' in record:
            response['last_verified_audit'] = record['last_verified_audit']
        return self._record('read_full', {'record_id': record_id, 'reason': reason},
                            response, True, started, record,
                            content_bytes=len(record['content'].encode('utf-8')))

    def read_heading_map(self, record_id):
        started = time.perf_counter_ns()
        record = self.state.get(record_id)
        if record is None:
            return self._record('read_heading_map', {'record_id': record_id}, None,
                                False, started, error='unknown synthetic record')
        response = {
            'record_id': record['id'], 'path': record['path'],
            'version': record['version'], 'headings': headings_for(record['content']),
        }
        return self._record('read_heading_map', {'record_id': record_id}, response,
                            True, started, record,
                            content_bytes=len(canonical_json(response['headings']).encode('utf-8')))

    def read_section(self, record_id, anchor):
        started = time.perf_counter_ns()
        record = self.state.get(record_id)
        request = {'record_id': record_id, 'anchor': anchor}
        if record is None:
            return self._record('read_section', request, None, False, started,
                                error='unknown synthetic record')
        heading = next((item for item in headings_for(record['content'])
                        if item['anchor'] == anchor), None)
        if heading is None:
            return self._record('read_section', request, None, False, started,
                                record=record, error='unknown Markdown anchor')
        raw = record['content'].encode('utf-8')
        section_bytes = raw[heading['start_byte']:heading['end_byte']]
        response = {
            'record_id': record['id'], 'path': record['path'],
            'version': record['version'], 'anchor': anchor,
            'start_byte': heading['start_byte'], 'end_byte': heading['end_byte'],
            'content': section_bytes.decode('utf-8'),
            'content_sha256': sha256_bytes(section_bytes),
        }
        return self._record('read_section', request, response, True, started, record,
                            content_bytes=len(section_bytes))

    def save_append(self, request):
        started = time.perf_counter_ns()
        authorization = self.controller_control.get('update_authorization')
        record = self.state.get(request.get('record_id'))
        request_bytes = len(canonical_json(request).encode('utf-8'))
        expected_request = ({
            'op': SAVE_OP,
            'record_id': authorization.get('record_id'),
            'expected_version': authorization.get('expected_version'),
            'append_text': authorization.get('append_text'),
        } if isinstance(authorization, dict) else None)
        prior_save = any(event.get('op') == SAVE_OP and event.get('ok')
                         for event in self.trace)
        if (not expected_request or request != expected_request or prior_save
                or not record or record.get('version') != authorization.get('expected_version')):
            self._record(
                SAVE_OP, request, None, False, started, record=record,
                error='save is not authorized for this scenario, record, version or content',
                request_bytes=request_bytes,
                pre_write_version=record.get('version') if record else None,
            )
            return {
                'ok': False,
                'error': 'save is not authorized for this scenario, record, version or content',
            }

        previous_version = record['version']
        saved = copy.deepcopy(record)
        saved['version'] = authorization['new_version']
        saved['content'] += authorization['append_text']
        self.state[saved['id']] = saved
        write_json(self.controller_root / 'state.json', self.state)
        write_bytes = len(authorization['append_text'].encode('utf-8'))
        response = {
            'ok': True,
            'record_id': saved['id'],
            'previous_version': previous_version,
            'version': saved['version'],
            'appended_bytes': write_bytes,
            'content_sha256': sha256_bytes(saved['content'].encode('utf-8')),
        }
        return self._record(
            SAVE_OP, request, response, True, started, record=record,
            request_bytes=request_bytes, write_bytes=write_bytes,
            pre_write_version=previous_version, post_write_version=saved['version'],
        )

    def stage_index_maintenance(self, request):
        started = time.perf_counter_ns()
        authorization = self.controller_control.get('maintenance_authorization')
        record = self.state.get('index')
        request_bytes = len(canonical_json(request).encode('utf-8'))
        content = request.get('candidate_content')
        stage_path = self.controller_root / 'staged-index.json'
        valid = (
            isinstance(authorization, dict)
            and set(request) == {
                'op', 'record_id', 'expected_version', 'candidate_content',
            }
            and request.get('op') == STAGE_MAINTENANCE_OP
            and request.get('record_id') == authorization.get('record_id') == 'index'
            and request.get('expected_version') == authorization.get('expected_version')
            and record is not None
            and record.get('version') == authorization.get('expected_version')
            and isinstance(content, str) and content.strip()
        )
        if not valid:
            self._record(
                STAGE_MAINTENANCE_OP, request, None, False, started, record=record,
                error='index maintenance staging is not authorized for this scenario or version',
                request_bytes=request_bytes,
            )
            return {'ok': False, 'error': 'index maintenance staging is not authorized'}

        candidate_content = content.encode('utf-8')
        content_bytes = len(candidate_content)
        candidate_sha256 = sha256_bytes(candidate_content)
        stage_id = maintenance_stage_id(
            'index', authorization['expected_version'], candidate_sha256)
        staged = {
            'stage_id': stage_id,
            'record_id': 'index',
            'expected_version': authorization['expected_version'],
            'candidate_sha256': candidate_sha256,
            'candidate_bytes': content_bytes,
            'candidate_content': content,
        }
        response = {
            'ok': True,
            'stage_id': stage_id,
            'record_id': 'index',
            'expected_version': authorization['expected_version'],
            'candidate_sha256': candidate_sha256,
            'candidate_bytes': content_bytes,
            'candidate_content': content,
        }
        missing_stage = object()
        try:
            existing_stage = json.loads(stage_path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            existing_stage = missing_stage
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            existing_stage = None
        if existing_stage is not missing_stage:
            if existing_stage != staged:
                self._record(
                    STAGE_MAINTENANCE_OP, request, None, False, started, record=record,
                    error='a conflicting or unreadable maintenance stage already exists',
                    request_bytes=request_bytes,
                )
                return {'ok': False, 'error': 'a conflicting maintenance stage already exists'}
            return self._record(
                STAGE_MAINTENANCE_OP, request, response, True, started, record=record,
                request_bytes=request_bytes,
            )
        write_json_atomic(stage_path, staged)
        return self._record(
            STAGE_MAINTENANCE_OP, request, response, True, started, record=record,
            request_bytes=request_bytes, write_bytes=content_bytes,
        )

    def promote_index_maintenance(self, request):
        started = time.perf_counter_ns()
        try:
            controller_control = json.loads(
                (self.controller_root / 'control.json').read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            controller_control = {}
        if not isinstance(controller_control, dict):
            controller_control = {}
        self.controller_control = controller_control
        authorization = self.controller_control.get('maintenance_authorization')
        approval = self.controller_control.get('maintenance_approval')
        record = self.state.get('index')
        request_bytes = len(canonical_json(request).encode('utf-8'))
        stage_path = self.controller_root / 'staged-index.json'
        try:
            staged = json.loads(stage_path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            staged = None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            staged = None
        staged_digest_valid = _staged_candidate_is_valid(staged, authorization)
        prior_promotion = any(
            event.get('op') == PROMOTE_MAINTENANCE_OP and event.get('ok')
            for event in self.trace
        )
        valid = (
            isinstance(authorization, dict)
            and isinstance(approval, dict) and approval.get('approved') is True
            and isinstance(staged, dict)
            and staged_digest_valid
            and set(request) == {
                'op', 'record_id', 'expected_version', 'stage_id',
                'candidate_sha256', 'approval_id',
            }
            and request.get('op') == PROMOTE_MAINTENANCE_OP
            and request.get('record_id') == authorization.get('record_id') == 'index'
            and request.get('expected_version') == authorization.get('expected_version')
            and record is not None
            and record.get('version') == authorization.get('expected_version')
            and request.get('stage_id') == staged.get('stage_id') == approval.get('stage_id')
            and request.get('candidate_sha256') == staged.get('candidate_sha256')
            == approval.get('candidate_sha256')
            and request.get('approval_id') == approval.get('approval_id')
            and approval.get('record_id') == authorization.get('record_id')
            and approval.get('expected_version') == authorization.get('expected_version')
            and approval.get('completed_date') == authorization.get('completed_date')
            and not prior_promotion
        )
        if not valid:
            self._record(
                PROMOTE_MAINTENANCE_OP, request, None, False, started, record=record,
                error='index promotion lacks matching case-specific approval or current version',
                request_bytes=request_bytes,
                pre_write_version=record.get('version') if record else None,
            )
            return {'ok': False, 'error': 'index promotion is not authorized'}

        promoted = copy.deepcopy(record)
        promoted['content'] = staged['candidate_content']
        promoted['version'] = authorization['new_version']
        promoted['last_verified_audit'] = authorization['completed_date']
        self.state['index'] = promoted
        write_json(self.controller_root / 'state.json', self.state)
        response = {
            'ok': True,
            'record_id': 'index',
            'previous_version': record['version'],
            'version': promoted['version'],
            'previous_content_sha256': sha256_bytes(record['content'].encode('utf-8')),
            'content_sha256': sha256_bytes(promoted['content'].encode('utf-8')),
            'last_verified_audit': promoted['last_verified_audit'],
            'candidate_sha256': staged['candidate_sha256'],
        }
        return self._record(
            PROMOTE_MAINTENANCE_OP, request, response, True, started, record=record,
            request_bytes=request_bytes, write_bytes=staged['candidate_bytes'],
            pre_write_version=record['version'], post_write_version=promoted['version'],
        )

    def call(self, request):
        op = request.get('op')
        if op == 'read_full':
            return self.read_full(request.get('record_id'), request.get('reason', 'candidate'))
        if op == 'read_heading_map':
            return self.read_heading_map(request.get('record_id'))
        if op == 'read_section':
            return self.read_section(request.get('record_id'), request.get('anchor'))
        if op == SAVE_OP:
            return self.save_append(request)
        if op == STAGE_MAINTENANCE_OP:
            return self.stage_index_maintenance(request)
        if op == PROMOTE_MAINTENANCE_OP:
            return self.promote_index_maintenance(request)
        started = time.perf_counter_ns()
        self._record(op or 'unknown', request, None, False, started,
                     record=self.state.get(request.get('record_id')),
                     error='operation is outside the authorized benchmark tool envelope')
        return {'ok': False, 'error': 'operation is outside the authorized benchmark tool envelope'}

    def snapshot(self):
        state = copy.deepcopy(self.state)
        write_json(self.controller_root / 'final-state.json', state)
        return state


def authorize_index_maintenance(root, *, stage_id, candidate_sha256,
                                approval_id, approved):
    """Record an out-of-band decision bound to one staged candidate hash."""
    root = Path(root)
    controller_root = root / 'controller'
    control_path = controller_root / 'control.json'
    control = json.loads(control_path.read_text(encoding='utf-8'))
    authorization = control.get('maintenance_authorization')
    stage_path = controller_root / 'staged-index.json'
    if not isinstance(authorization, dict):
        raise ValueError('no authorized maintenance candidate is available for approval')
    try:
        staged = json.loads(stage_path.read_text(encoding='utf-8'))
    except FileNotFoundError as error:
        raise ValueError('no authorized maintenance candidate is available for approval') from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('staged candidate is not readable JSON') from error
    digest_valid = _staged_candidate_is_valid(staged, authorization)
    if (control.get('maintenance_approval') is not None
            or not digest_valid
            or stage_id != staged.get('stage_id')
            or candidate_sha256 != staged.get('candidate_sha256')
            or not isinstance(approval_id, str) or not approval_id.strip()
            or not isinstance(approved, bool)):
        raise ValueError('approval must identify the exact staged candidate and decision')
    approval = {
        'approved': approved,
        'approval_id': approval_id,
        'stage_id': stage_id,
        'candidate_sha256': candidate_sha256,
        'record_id': authorization['record_id'],
        'expected_version': authorization['expected_version'],
        'completed_date': authorization['completed_date'],
        'evidence_kind': 'out-of-band-scripted-consent',
    }
    control['maintenance_approval'] = approval
    write_json(control_path, control)
    receipt_path = controller_root / 'receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    receipt['maintenance_approval'] = copy.deepcopy(approval)
    write_json(receipt_path, receipt)
    return copy.deepcopy(approval)


def serve(root):
    """Expose the public synthetic tools over MCP stdio."""
    import sys

    adapter = FixtureAdapter(root)
    available = adapter.public()['tools']
    schemas = {
        'read_full': {
            'type': 'object', 'properties': {
                'record_id': {'type': 'string'},
                'reason': {'type': 'string', 'enum': ['candidate', 'fallback']},
            }, 'required': ['record_id'],
        },
        'read_heading_map': {
            'type': 'object', 'properties': {'record_id': {'type': 'string'}},
            'required': ['record_id'],
        },
        'read_section': {
            'type': 'object', 'properties': {
                'record_id': {'type': 'string'}, 'anchor': {'type': 'string'},
            }, 'required': ['record_id', 'anchor'],
        },
        SAVE_OP: {
            'type': 'object', 'properties': {
                'record_id': {'type': 'string'},
                'expected_version': {'type': 'string'},
                'append_text': {'type': 'string'},
            }, 'required': ['record_id', 'expected_version', 'append_text'],
            'additionalProperties': False,
        },
        STAGE_MAINTENANCE_OP: {
            'type': 'object', 'properties': {
                'record_id': {'type': 'string'},
                'expected_version': {'type': 'string'},
                'candidate_content': {'type': 'string'},
            }, 'required': ['record_id', 'expected_version', 'candidate_content'],
            'additionalProperties': False,
        },
        PROMOTE_MAINTENANCE_OP: {
            'type': 'object', 'properties': {
                'record_id': {'type': 'string'},
                'expected_version': {'type': 'string'},
                'stage_id': {'type': 'string'},
                'candidate_sha256': {'type': 'string'},
                'approval_id': {'type': 'string'},
            }, 'required': [
                'record_id', 'expected_version', 'stage_id',
                'candidate_sha256', 'approval_id',
            ],
            'additionalProperties': False,
        },
    }
    for line in sys.stdin:
        request = json.loads(line)
        if 'id' not in request:
            continue
        method = request.get('method')
        params = request.get('params', {})
        response = {'jsonrpc': '2.0', 'id': request['id']}
        if method == 'initialize':
            requested = params.get('protocolVersion')
            versions = ('2024-11-05', '2025-03-26', '2025-06-18', '2025-11-25')
            version = requested if requested in versions else '2025-11-25'
            response['result'] = {
                'protocolVersion': version, 'capabilities': {'tools': {}},
                'serverInfo': {'name': 'remember-me-synthetic-benchmark', 'version': '1.1.0'},
            }
        elif method == 'ping':
            response['result'] = {}
        elif method == 'tools/list':
            descriptions = {
                SAVE_OP: 'Apply one controller-authorized synthetic append.',
                STAGE_MAINTENANCE_OP: 'Stage a synthetic index candidate beside recoverable state.',
                PROMOTE_MAINTENANCE_OP: 'Promote only the staged digest with matching out-of-band approval.',
            }
            response['result'] = {'tools': [
                {'name': name,
                 'description': descriptions.get(
                     name, f'Read synthetic benchmark data using {name}.'),
                 'inputSchema': schemas[name]}
                for name in available
            ]}
        elif method == 'tools/call':
            arguments = params.get('arguments') if isinstance(params, dict) else None
            name = params.get('name') if isinstance(params, dict) else None
            if not isinstance(name, str) or not isinstance(arguments, dict):
                response['error'] = {
                    'code': -32602,
                    'message': 'Tool call requires a string name and object arguments',
                }
            else:
                result = adapter.call({'op': name, **arguments})
                response['result'] = {
                    'content': [{'type': 'text', 'text': json.dumps(result, ensure_ascii=False)}],
                    'isError': not adapter.trace[-1].get('ok', False),
                }
        else:
            response['error'] = {'code': -32601, 'message': 'Unknown benchmark method or tool'}
        print(json.dumps(response, ensure_ascii=False), flush=True)


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['serve', 'call', 'snapshot'])
    parser.add_argument('root', type=Path)
    parser.add_argument('--request', help='one JSON read-tool request')
    args = parser.parse_args()
    if args.action == 'serve':
        serve(args.root)
    elif args.action == 'call':
        if not args.request:
            parser.error('call requires --request')
        print(json.dumps(FixtureAdapter(args.root).call(json.loads(args.request)),
                         ensure_ascii=False))
    else:
        print(json.dumps(FixtureAdapter(args.root).snapshot(), ensure_ascii=False))


if __name__ == '__main__':
    main()
