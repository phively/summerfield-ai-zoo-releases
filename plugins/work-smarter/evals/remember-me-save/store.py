#!/usr/bin/env python3
"""Synthetic test-only provider. Never connect this adapter to real personal records."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFEST = Path(__file__).with_name('manifest.json')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def initialize(root, case_id, candidate, evidence_kind="activated-skill"):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise FileExistsError('Use a unique empty trial root')
    case = next(c for c in read_json(MANIFEST)['cases'] if c['id'] == case_id)
    write_json(root / 'control.json', case)
    write_json(root / 'state.json', case['initial'])
    write_json(root / 'public.json', case['public'])
    write_json(root / 'receipt.json', dict(case_id=case_id, case_hash=digest(case),
                                          candidate_hash=digest(candidate), candidate=candidate,
                                          evidence_kind=evidence_kind))
    write_json(root / 'turns.json', [dict(role='user', content=case['public']['prompt'])])
    (root / 'events.jsonl').touch()


class Store:
    def __init__(self, root):
        self.root = Path(root)

    def call(self, request):
        state = read_json(self.root / 'state.json')
        control = read_json(self.root / 'control.json')
        events_path = self.root / 'events.jsonl'
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        turns = read_json(self.root / 'turns.json')
        op = request.get('op')
        rid = request.get('record', {}).get('id') if op == 'create' else request.get('id')
        record = state.get(rid)
        fault = control['faults'].get(f'{rid}:{op}')
        prior_write = any(e['record_id'] == rid and e['committed'] for e in events)
        committed = False
        result = {'ok': False, 'error': 'unknown operation or identity'}
        if op == 'list':
            result = {'ok': True, 'provider': 'fixture', 'container': control['public']['selected_container'],
                      'records': [{k: v for k, v in r.items() if k != 'content'} for r in state.values()]}
        elif op == 'create':
            new = request.get('record', {})
            rid = new.get('id')
            if rid and rid not in state and all(k in new for k in ('provider', 'container', 'path', 'owner', 'content')):
                state[rid] = new
                committed = True
                result = {'ok': True, 'id': rid}
                if fault == 'lost-ack':
                    result = {'ok': False, 'error': 'acknowledgement lost'}
        elif record and all(request.get(k) == record[k] for k in ('provider', 'container', 'id')):
            if op in ('read', 'metadata'):
                result = {'ok': True, 'record': json.loads(json.dumps(record))}
                if prior_write and fault == 'unavailable-after-write':
                    result = {'ok': False, 'error': 'readback unavailable'}
                elif op == 'metadata':
                    result['record']['content'] = {k: v for k, v in record['content'].items() if k in ('setup_confirmed', 'canonical_container', 'topic_id')}
                elif prior_write and fault == 'mismatch-after-write':
                    result['record']['content']['preference'] = 'mismatched provider readback'
            elif op in ('write', 'owner_update'):
                if op == 'write' and record['owner'] != 'remember-me':
                    result = {'ok': False, 'error': 'external owner only'}
                elif fault == 'reject':
                    result = {'ok': False, 'error': f'{rid} unavailable'}
                elif fault == 'done-only':
                    result = {'ok': True, 'message': 'done'}
                else:
                    record['content'].update(request.get('patch', {}))
                    committed = True
                    result = {'ok': True, 'id': rid}
                    if op == 'owner_update':
                        result['readback'] = json.loads(json.dumps(record))
                    if fault in ('lost-ack', 'lost-ack-conflict') and not prior_write:
                        if fault == 'lost-ack-conflict':
                            record['content']['preference'] = 'detailed answers (newer user correction)'
                        result = {'ok': False, 'error': 'acknowledgement lost'}
        write_json(self.root / 'state.json', state)
        event = dict(seq=len(events) + 1, turn=len(turns) - 1, request=request, result=result,
                     record_id=rid, committed=committed)
        with events_path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event) + '\n')
        return result


def snapshot(root):
    root = Path(root)
    state = read_json(root / 'state.json')
    write_json(root / 'final-state.json', state)
    return state


def serve(root):
    tools = read_json(Path(root) / 'public.json')['tools']
    for line in sys.stdin:
        request = json.loads(line)
        if 'id' not in request:
            continue
        method = request.get('method')
        params = request.get('params', {})
        response = {'jsonrpc': '2.0', 'id': request['id']}
        if method == 'initialize':
            requested = params.get('protocolVersion')
            version = requested if requested in ('2024-11-05', '2025-03-26', '2025-06-18', '2025-11-25') else '2025-11-25'
            response['result'] = dict(protocolVersion=version, capabilities={'tools': {}},
                                      serverInfo={'name': 'remember-me-synthetic-store', 'version': '1.0.0'})
        elif method == 'ping':
            response['result'] = {}
        elif method == 'tools/list':
            properties = {k: {'type': 'string'} for k in ('provider', 'container', 'id')}
            properties['provider']['enum'] = ['fixture']
            properties.update(
                patch={'type': 'object', 'description': 'Merge these fields directly into record.content; do not wrap them in a content key. JSON null stores a literal null, not deletion. Example: {"preference": "detailed answers"}.'},
                record={'type': 'object', 'description': 'For create only: provider, container, id, path, owner, content. Keep source metadata in separate content fields; content.markdown contains only the requested verbatim turn bodies.'})
            response['result'] = {'tools': [dict(name=name, description=f'Synthetic provider operation: {name}',
                inputSchema={'type': 'object', 'properties': properties}) for name in tools]}
        elif method == 'tools/call' and params.get('name') in tools:
            result = Store(root).call({**params.get('arguments', {}), 'op': params['name']})
            response['result'] = {'content': [{'type': 'text', 'text': json.dumps(result)}],
                                  'isError': not result['ok']}
        else:
            response['error'] = {'code': -32601, 'message': 'Unknown fixture method or tool'}
        print(json.dumps(response), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init', 'call', 'snapshot', 'reply', 'serve'])
    parser.add_argument('root', type=Path)
    parser.add_argument('--case')
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--request', help='one JSON tool request')
    parser.add_argument('--text', help='controller-recorded assistant proposal before scripted user reply')
    args = parser.parse_args()
    if args.action == 'init':
        initialize(args.root, args.case, read_json(args.candidate))
    elif args.action == 'call':
        print(json.dumps(Store(args.root).call(json.loads(args.request))))
    elif args.action == 'serve':
        serve(args.root)
    elif args.action == 'snapshot':
        print(json.dumps(snapshot(args.root)))
    else:
        case = read_json(args.root / 'control.json')
        turns = read_json(args.root / 'turns.json')
        if len(turns) != 1 or not case['approval_turn']:
            parser.error('No outstanding scripted reply')
        turns.extend([dict(role='assistant', content=args.text), dict(role='user', content=case['approval_turn']['reply'])])
        write_json(args.root / 'turns.json', turns)
        print(case['approval_turn']['reply'])


if __name__ == '__main__':
    main()
