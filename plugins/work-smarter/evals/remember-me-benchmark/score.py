import copy
import hashlib
import json
import re
from datetime import date


READ_OPS = frozenset({'read_full', 'read_heading_map', 'read_section'})
SAVE_OP = 'save_append'
STAGE_MAINTENANCE_OP = 'stage_index_maintenance'
PROMOTE_MAINTENANCE_OP = 'promote_index_maintenance'
INDEX_TRIGGER_TREATMENTS_KIB = frozenset({8, 32, 48, 64})


def canonical_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def sha256_json(value):
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


def _sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _maintenance_stage_id(record_id, expected_version, candidate_sha256):
    return 'index-maintenance-' + sha256_json({
        'record_id': record_id,
        'expected_version': expected_version,
        'candidate_sha256': candidate_sha256,
    })[:16]


def _slug(title):
    slug = re.sub(r'[^\w\- ]', '', title.lower(), flags=re.UNICODE)
    slug = re.sub(r'[\s_]+', '-', slug).strip('-')
    return slug or 'section'


def _headings_for(content):
    raw = content.encode('utf-8')
    result = []
    offset = 0
    counts = {}
    for line in content.splitlines(keepends=True):
        match = re.match(r'^(#{1,6})[ \t]+(.+?)\s*#*[ \t]*(?:\r?\n)?$', line)
        if match:
            level, title = len(match.group(1)), match.group(2).strip()
            base = _slug(title)
            occurrence = counts.get(base, 0)
            counts[base] = occurrence + 1
            result.append({'level': level, 'title': title,
                           'anchor': base if occurrence == 0 else f'{base}-{occurrence}',
                           'start_byte': offset})
        offset += len(line.encode('utf-8'))
    for index, heading in enumerate(result):
        heading['end_byte'] = len(raw)
        for following in result[index + 1:]:
            if following['level'] <= heading['level']:
                heading['end_byte'] = following['start_byte']
                break
    return result


def _headings_for_record(record_id, record, cache):
    cache_key = (record_id, record.get('version'), record.get('content'))
    if cache_key not in cache:
        cache[cache_key] = _headings_for(record['content'])
    return cache[cache_key]


def _check(passed, evidence, applicable=True):
    return {'passed': bool(passed), 'applicable': bool(applicable), 'evidence': evidence}


def _validate_trace(trace, initial_records, reference_records, gold, headings_cache,
                    maintenance_approval=None):
    valid = True
    section_events_valid = True
    errors = []
    unauthorized = []
    by_seq = {}
    record_snapshots = {}
    replay = copy.deepcopy(initial_records)
    authorized_saves = []
    maintenance_stage_sequences = []
    maintenance_stage_attempt_sequences = []
    maintenance_stage_retry_sequences = []
    authorized_maintenance_sequences = []
    staged_candidates = {}
    for index, event in enumerate(trace, 1):
        if not isinstance(event, dict) or event.get('seq') != index:
            valid = False
            errors.append(f'event {index} has a missing or out-of-order sequence number')
            continue
        by_seq[index] = event
        op = event.get('op')
        if not isinstance(event.get('elapsed_ns'), int) or event['elapsed_ns'] < 0:
            valid = False
            errors.append(f'event {index} has invalid monotonic timing')

        if op == SAVE_OP:
            request = event.get('request')
            authorization = gold.get('update_authorization')
            save_scope_valid = (
                gold.get('scenario_id') in (
                    'amortized-update-audit', 'closeout-sequence-40k')
                and isinstance(authorization, dict)
                and authorization.get('record_id') == 'topic-communication'
            )
            expected_request = ({
                'op': SAVE_OP,
                'record_id': authorization.get('record_id'),
                'expected_version': authorization.get('expected_version'),
                'append_text': authorization.get('append_text'),
            } if save_scope_valid else None)
            request_bytes = (len(canonical_json(request).encode('utf-8'))
                             if isinstance(request, dict) else None)
            target_id = (authorization.get('record_id')
                         if isinstance(authorization, dict) else None)
            record = replay.get(target_id) if target_id else None
            authorized_request = (
                expected_request is not None
                and request == expected_request
                and record is not None
                and record.get('version') == authorization.get('expected_version')
                and not authorized_saves
            )
            if (event.get('request_bytes') != request_bytes
                    or event.get('record_id') != (request.get('record_id')
                                                  if isinstance(request, dict) else None)):
                valid = False
                errors.append(f'event {index} has invalid save request accounting or target')
            if not authorized_request:
                unauthorized.append(index)
                valid = False
                errors.append(f'event {index} is an unauthorized synthetic save attempt')
                if (event.get('ok') or event.get('response') is not None
                        or event.get('returned_bytes') != 0
                        or event.get('write_bytes') != 0):
                    errors.append(f'event {index} claims effects for a rejected save')
                continue

            if not event.get('ok'):
                if (event.get('response') is not None or event.get('returned_bytes') != 0
                        or event.get('write_bytes') != 0):
                    valid = False
                    errors.append(f'failed save event {index} carries effects or a response')
                continue

            append_text = authorization['append_text']
            write_bytes = len(append_text.encode('utf-8'))
            previous_version = record['version']
            new_record = copy.deepcopy(record)
            new_record['content'] += append_text
            new_record['version'] = authorization['new_version']
            response = {
                'ok': True,
                'record_id': target_id,
                'previous_version': previous_version,
                'version': authorization['new_version'],
                'appended_bytes': write_bytes,
                'content_sha256': _sha256_bytes(new_record['content'].encode('utf-8')),
            }
            payload = canonical_json(response).encode('utf-8')
            if (event.get('record_version') != previous_version
                    or event.get('pre_write_version') != previous_version
                    or event.get('post_write_version') != authorization['new_version']
                    or event.get('content_bytes') != 0
                    or event.get('write_bytes') != write_bytes
                    or event.get('response') != response
                    or event.get('returned_bytes') != len(payload)
                    or event.get('response_sha256') != _sha256_bytes(payload)):
                valid = False
                unauthorized.append(index)
                errors.append(f'event {index} does not prove the authorized save delta')
                continue

            replay[target_id] = new_record
            authorized_saves.append(index)
            continue

        if op == STAGE_MAINTENANCE_OP:
            maintenance_stage_attempt_sequences.append(index)
            request = event.get('request')
            authorization = gold.get('maintenance_authorization')
            request_bytes = (len(canonical_json(request).encode('utf-8'))
                             if isinstance(request, dict) else None)
            target_id = (authorization.get('record_id')
                         if isinstance(authorization, dict) else None)
            record = replay.get(target_id) if target_id else None
            content = request.get('candidate_content') if isinstance(request, dict) else None
            candidate_raw = content.encode('utf-8') if isinstance(content, str) else None
            candidate_bytes = len(candidate_raw) if candidate_raw is not None else None
            candidate_sha256 = (_sha256_bytes(candidate_raw)
                                if candidate_raw is not None else None)
            stage_id = (_maintenance_stage_id(
                target_id, authorization.get('expected_version'), candidate_sha256)
                if isinstance(authorization, dict) and candidate_sha256 else None)
            staged = staged_candidates.get(stage_id)
            exact_retry = bool(
                staged
                and staged.get('record_id') == target_id
                and staged.get('expected_version') == authorization.get('expected_version')
                and staged.get('candidate_sha256') == candidate_sha256
                and staged.get('candidate_bytes') == candidate_bytes
                and staged.get('candidate_content') == content
            )
            stage_valid = (
                isinstance(authorization, dict)
                and isinstance(request, dict)
                and set(request) == {
                    'op', 'record_id', 'expected_version', 'candidate_content',
                }
                and request.get('op') == STAGE_MAINTENANCE_OP
                and request.get('record_id') == target_id == 'index'
                and request.get('expected_version') == authorization.get('expected_version')
                and isinstance(record, dict)
                and record.get('version') == authorization.get('expected_version')
                and isinstance(content, str) and bool(content.strip())
                and (not maintenance_stage_sequences or exact_retry)
            )
            if (event.get('request_bytes') != request_bytes
                    or event.get('record_id') != (request.get('record_id')
                                                  if isinstance(request, dict) else None)):
                valid = False
                errors.append(f'event {index} has invalid maintenance-stage accounting or target')
            if not stage_valid:
                unauthorized.append(index)
                valid = False
                errors.append(f'event {index} is an unauthorized maintenance stage')
                if (event.get('ok') or event.get('response') is not None
                        or event.get('returned_bytes') != 0
                        or event.get('write_bytes') != 0):
                    errors.append(f'event {index} claims effects for a rejected maintenance stage')
                continue
            if not event.get('ok'):
                valid = False
                errors.append(f'authorized maintenance stage {index} failed')
                continue

            response = {
                'ok': True,
                'stage_id': stage_id,
                'record_id': target_id,
                'expected_version': authorization['expected_version'],
                'candidate_sha256': candidate_sha256,
                'candidate_bytes': candidate_bytes,
                'candidate_content': content,
            }
            payload = canonical_json(response).encode('utf-8')
            if (event.get('record_version') != record.get('version')
                    or event.get('content_bytes') != 0
                    or event.get('write_bytes') != (0 if exact_retry else candidate_bytes)
                    or event.get('response') != response
                    or event.get('returned_bytes') != len(payload)
                    or event.get('response_sha256') != _sha256_bytes(payload)):
                valid = False
                unauthorized.append(index)
                errors.append(f'event {index} does not prove the staged candidate bytes')
                continue
            if exact_retry:
                maintenance_stage_retry_sequences.append(index)
            else:
                staged_candidates[stage_id] = {
                    'record_id': target_id,
                    'expected_version': authorization['expected_version'],
                    'candidate_sha256': candidate_sha256,
                    'candidate_bytes': candidate_bytes,
                    'candidate_content': content,
                    'stage_sequence': index,
                }
                maintenance_stage_sequences.append(index)
            continue

        if op == PROMOTE_MAINTENANCE_OP:
            request = event.get('request')
            authorization = gold.get('maintenance_authorization')
            approval = maintenance_approval if isinstance(maintenance_approval, dict) else None
            request_bytes = (len(canonical_json(request).encode('utf-8'))
                             if isinstance(request, dict) else None)
            target_id = (authorization.get('record_id')
                         if isinstance(authorization, dict) else None)
            record = replay.get(target_id) if target_id else None
            stage_id = request.get('stage_id') if isinstance(request, dict) else None
            staged = staged_candidates.get(stage_id)
            prior_promotion = bool(authorized_maintenance_sequences)
            request_fields = request if isinstance(request, dict) else {}
            approval_valid = bool(
                authorization and staged and approval
                and approval.get('approved') is True
                and approval.get('evidence_kind') == 'out-of-band-scripted-consent'
                and approval.get('approval_id') == request_fields.get('approval_id')
                and approval.get('stage_id') == stage_id
                and approval.get('candidate_sha256') == staged.get('candidate_sha256')
                and approval.get('record_id') == authorization.get('record_id')
                and approval.get('expected_version') == authorization.get('expected_version')
                and approval.get('completed_date') == authorization.get('completed_date')
            )
            promotion_valid = (
                isinstance(authorization, dict)
                and isinstance(request, dict)
                and set(request) == {
                    'op', 'record_id', 'expected_version', 'stage_id',
                    'candidate_sha256', 'approval_id',
                }
                and request.get('op') == PROMOTE_MAINTENANCE_OP
                and request.get('record_id') == target_id == 'index'
                and request.get('expected_version') == authorization.get('expected_version')
                and isinstance(record, dict)
                and record.get('version') == authorization.get('expected_version')
                and isinstance(staged, dict)
                and request.get('candidate_sha256') == staged.get('candidate_sha256')
                and approval_valid and not prior_promotion
            )
            if (event.get('request_bytes') != request_bytes
                    or event.get('record_id') != (request.get('record_id')
                                                  if isinstance(request, dict) else None)):
                valid = False
                errors.append(f'event {index} has invalid maintenance-promotion accounting or target')
            if not promotion_valid:
                unauthorized.append(index)
                valid = False
                errors.append(f'event {index} is an unauthorized maintenance promotion')
                if (event.get('ok') or event.get('response') is not None
                        or event.get('returned_bytes') != 0
                        or event.get('write_bytes') != 0):
                    errors.append(f'event {index} claims effects for a rejected promotion')
                continue
            if not event.get('ok'):
                valid = False
                errors.append(f'approved maintenance promotion {index} failed')
                continue

            new_record = copy.deepcopy(record)
            new_record['content'] = staged['candidate_content']
            new_record['version'] = authorization['new_version']
            new_record['last_verified_audit'] = authorization['completed_date']
            response = {
                'ok': True,
                'record_id': target_id,
                'previous_version': record['version'],
                'version': authorization['new_version'],
                'previous_content_sha256': _sha256_bytes(record['content'].encode('utf-8')),
                'content_sha256': _sha256_bytes(new_record['content'].encode('utf-8')),
                'last_verified_audit': authorization['completed_date'],
                'candidate_sha256': staged['candidate_sha256'],
            }
            payload = canonical_json(response).encode('utf-8')
            if (event.get('record_version') != record.get('version')
                    or event.get('pre_write_version') != record.get('version')
                    or event.get('post_write_version') != authorization['new_version']
                    or event.get('content_bytes') != 0
                    or event.get('write_bytes') != staged['candidate_bytes']
                    or event.get('response') != response
                    or event.get('returned_bytes') != len(payload)
                    or event.get('response_sha256') != _sha256_bytes(payload)):
                valid = False
                unauthorized.append(index)
                errors.append(f'event {index} does not prove the approved maintenance transition')
                continue
            replay[target_id] = new_record
            authorized_maintenance_sequences.append(index)
            continue

        if op not in READ_OPS:
            valid = False
            unauthorized.append(index)
            errors.append(f'event {index} is outside the authorized tool envelope')
            continue

        record_id = event.get('record_id')
        record = replay.get(record_id)
        if not event.get('ok'):
            if event.get('response') is not None or event.get('returned_bytes') != 0:
                valid = False
                errors.append(f'failed event {index} carries an unverified response')
            if op == 'read_section':
                section_events_valid = False
            continue

        response = event.get('response')
        if not isinstance(record, dict) or not isinstance(response, dict):
            valid = False
            errors.append(f'event {index} cannot be bound to independent record readback')
            if op == 'read_section':
                section_events_valid = False
            continue
        payload = canonical_json(response).encode('utf-8')
        if (event.get('record_version') != record.get('version')
                or response.get('record_id') != record_id
                or response.get('path') != record.get('path')
                or response.get('version') != record.get('version')
                or event.get('returned_bytes') != len(payload)
                or event.get('response_sha256') != _sha256_bytes(payload)):
            valid = False
            errors.append(f'event {index} identity, returned-byte count or response hash is invalid')
            if op == 'read_section':
                section_events_valid = False
            continue

        content = record.get('content', '')
        raw = content.encode('utf-8')
        if op == 'read_full':
            expected_content_bytes = len(raw)
            response_ok = (response.get('kind') == record.get('kind')
                           and response.get('content') == content
                           and response.get('content_sha256') == _sha256_bytes(raw)
                           and event.get('request', {}).get('record_id') == record_id
                           and response.get('reason') in ('candidate', 'fallback')
                           and ('last_verified_audit' in response)
                           == ('last_verified_audit' in record)
                           and response.get('last_verified_audit')
                           == record.get('last_verified_audit'))
        elif op == 'read_heading_map':
            expected_headings = _headings_for_record(record_id, record, headings_cache)
            expected_content_bytes = len(canonical_json(expected_headings).encode('utf-8'))
            response_ok = (response.get('headings') == expected_headings
                           and event.get('request', {}).get('record_id') == record_id)
        else:
            anchor = event.get('request', {}).get('anchor')
            heading = next((item for item in _headings_for_record(record_id, record, headings_cache)
                            if item['anchor'] == anchor), None)
            response_ok = False
            expected_content_bytes = 0
            if heading:
                expected_bytes = raw[heading['start_byte']:heading['end_byte']]
                expected_content_bytes = len(expected_bytes)
                response_ok = (
                    response.get('anchor') == anchor
                    and response.get('start_byte') == heading['start_byte']
                    and response.get('end_byte') == heading['end_byte']
                    and response.get('content') == expected_bytes.decode('utf-8')
                    and response.get('content_sha256') == _sha256_bytes(expected_bytes)
                )
            if not response_ok:
                section_events_valid = False
        if not response_ok or event.get('content_bytes') != expected_content_bytes:
            valid = False
            errors.append(f'event {index} does not prove the bytes it claims to return')
            if op == 'read_section':
                section_events_valid = False
            continue
        record_snapshots[index] = copy.deepcopy(record)

    if replay != reference_records:
        valid = False
        errors.append('replayed trace state does not match the independent final-state snapshot')
    return {
        'passed': valid,
        'errors': errors,
        'events_by_seq': by_seq,
        'record_snapshots_by_seq': record_snapshots,
        'section_events_valid': section_events_valid,
        'unauthorized_event_sequences': unauthorized,
        'authorized_save_sequences': authorized_saves,
        'maintenance_stage_sequences': maintenance_stage_sequences,
        'maintenance_stage_attempt_sequences': maintenance_stage_attempt_sequences,
        'maintenance_stage_retry_sequences': maintenance_stage_retry_sequences,
        'authorized_maintenance_sequences': authorized_maintenance_sequences,
        'staged_candidates': staged_candidates,
        'replayed_state': replay,
    }


def _normalized_text(value):
    if not isinstance(value, str):
        return ''
    return ' '.join(value.casefold().split())


def _matches_recorded_value(expected, observed):
    expected_text = _normalized_text(expected)
    observed_text = _normalized_text(observed)
    return bool(expected_text and expected_text in observed_text)


def _matches_recorded_uncertainty(expected, observed):
    expected_text = _normalized_text(expected)
    observed_text = _normalized_text(observed)
    if expected_text == 'none':
        return (observed_text == 'none' or 'no uncertainty' in observed_text
                or 'no further uncertainty' in observed_text
                or 'not uncertain' in observed_text)
    if expected_text == 'unconfirmed':
        return 'unconfirm' in observed_text or 'not a commitment' in observed_text
    if expected_text == 'superseded':
        return 'supersed' in observed_text
    return bool(expected_text and expected_text in observed_text)


def _answer_checks(answer, gold, reference_records, trace_check, headings_cache):
    answer_facts = answer.get('facts', {}) if isinstance(answer, dict) else {}
    if not isinstance(answer_facts, dict):
        answer_facts = {}
    required = {fact['id']: fact for fact in gold.get('required_facts', [])}
    required_fact_ids_by_public_location = {
        (fact['authority_id'], fact['anchor']): fact_id
        for fact_id, fact in required.items()
    }
    mapped_answers = {}
    extras = []
    for label, response in answer_facts.items():
        if not isinstance(response, dict):
            extras.append(label)
            continue
        location = (response.get('authority_id'), response.get('anchor'))
        fact_id = required_fact_ids_by_public_location.get(location)
        if fact_id is None or fact_id in mapped_answers:
            extras.append(label)
        else:
            mapped_answers[fact_id] = response
    missing = sorted(set(required) - set(mapped_answers))
    content_mismatches = []
    for fact_id, fact in required.items():
        response = mapped_answers.get(fact_id)
        if not isinstance(response, dict):
            continue
        field_matches = {
            'value': _matches_recorded_value(fact['value'], response.get('value')),
            'attribution': _matches_recorded_value(
                fact['attribution'], response.get('attribution')),
            'uncertainty': _matches_recorded_uncertainty(
                fact['uncertainty'], response.get('uncertainty')),
            'authority_id': response.get('authority_id') == fact['authority_id'],
            'anchor': response.get('anchor') == fact['anchor'],
        }
        failed_fields = sorted(key for key, passed in field_matches.items() if not passed)
        if failed_fields:
            content_mismatches.append({'fact_id': fact_id, 'fields': failed_fields})
    claims = answer.get('claims', []) if isinstance(answer, dict) else []
    unsupported_claims = []
    if isinstance(claims, list):
        for claim in claims:
            if not isinstance(claim, dict):
                unsupported_claims.append(claim)
                continue
            fact_id = required_fact_ids_by_public_location.get(
                (claim.get('authority_id'), claim.get('anchor')))
            if fact_id is None or claim.get('value') != required[fact_id]['value']:
                unsupported_claims.append(claim)
    else:
        unsupported_claims.append('claims must be a list when supplied')
    recall = not missing and not extras and not unsupported_claims and not content_mismatches

    evidence_errors = []
    for fact_id, fact in required.items():
        response = mapped_answers.get(fact_id)
        if not isinstance(response, dict):
            evidence_errors.append(f'{fact_id}: answer item is absent')
            continue
        citations = response.get('evidence', [])
        supported = False
        for citation in citations if isinstance(citations, list) else []:
            if not isinstance(citation, dict):
                continue
            event = trace_check['events_by_seq'].get(citation.get('event_seq'))
            if not event or not event.get('ok'):
                continue
            record_id = fact['authority_id']
            record = trace_check['record_snapshots_by_seq'].get(citation.get('event_seq'))
            if (not record or event.get('record_id') != record_id
                    or citation.get('record_id') != record_id
                    or citation.get('version') != event.get('record_version')
                    or event.get('record_version') != record.get('version')
                    or citation.get('anchor') != fact['anchor']
                    or citation.get('response_sha256') != event.get('response_sha256')):
                continue
            response_content = event.get('response', {}).get('content', '')
            if (event.get('op') == 'read_section'
                    and event.get('response', {}).get('anchor') != fact['anchor']):
                continue
            if fact['value'] not in response_content:
                continue
            if fact['anchor'] not in {
                h['anchor'] for h in _headings_for_record(record_id, record, headings_cache)
            }:
                continue
            supported = True
            break
        if not supported:
            evidence_errors.append(f'{fact_id}: no trace-backed authoritative evidence')
    return {
        'complete_recall': _check(recall, {
            'missing': missing, 'unexpected': extras,
            'unsupported_claims': unsupported_claims,
            'content_mismatches': content_mismatches,
        }),
        'evidence_support': _check(not evidence_errors, evidence_errors),
    }


def _one_usage_measurement(usage):
    measured = {'status': 'unavailable', 'source': 'unavailable',
                'input_tokens': None, 'output_tokens': None,
                'cached_input_tokens': None, 'actual_total_tokens': None,
                'estimate': None}
    if not isinstance(usage, dict):
        return measured
    source = usage.get('source')
    if source == 'tokenizer_estimate':
        tokens = usage.get('tokens')
        tokenizer = usage.get('tokenizer')
        version = usage.get('tokenizer_version')
        if isinstance(tokens, int) and not isinstance(tokens, bool) and tokens >= 0 and tokenizer and version:
            measured['estimate'] = {'tokens': tokens, 'tokenizer': tokenizer,
                                    'tokenizer_version': version}
        return measured
    if source != 'provider_reported':
        return measured
    measured['source'] = source
    for key in ('input_tokens', 'output_tokens', 'cached_input_tokens'):
        value = usage.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            measured[key] = value
    if measured['input_tokens'] is not None and measured['output_tokens'] is not None:
        measured['status'] = 'available'
        # Cached input is a subset of input tokens, so it is reported separately.
        measured['actual_total_tokens'] = measured['input_tokens'] + measured['output_tokens']
    elif measured['input_tokens'] is not None or measured['output_tokens'] is not None:
        measured['status'] = 'partial'
    return measured


def _usage_measurement(usage):
    measured = _one_usage_measurement(usage)
    phases = usage.get('phases', {}) if isinstance(usage, dict) else {}
    phases = phases if isinstance(phases, dict) else {}
    phase_names = {'read', 'update', 'audit'} | {str(name) for name in phases}
    measured['by_phase'] = {
        phase: _one_usage_measurement(phases.get(phase))
        for phase in sorted(phase_names)
    }
    return measured


def _audit_checks(gold, answer, reference_records, trace, trace_check):
    pointers = gold.get('pointer_targets', [])
    missing_pointers = sorted(set(pointers) - set(reference_records))
    index_text = reference_records.get('index', {}).get('content', '')
    unreferenced_pointers = sorted(pointer for pointer in pointers if pointer not in index_text)
    control = gold.get('scenario_control', {})
    stale_anchor = control.get('stale_anchor')
    navigation_used = any(event.get('op') in ('read_heading_map', 'read_section')
                          for event in trace)
    fallback_target = control.get('stale_anchor_target')
    missing_fallback = bool(stale_anchor and navigation_used and not any(
        event.get('op') == 'read_full' and event.get('ok')
        and event.get('record_id') == fallback_target
        and event.get('response', {}).get('reason') == 'fallback'
        for event in trace))
    pointer_ok = not missing_pointers and not unreferenced_pointers and not missing_fallback

    if not gold.get('audit_required'):
        protected = _check(True, 'No staged audit is required for this scenario.', applicable=False)
    else:
        missing_from_records = []
        headings_cache = {}
        if gold.get('scenario_id') in (
                'amortized-update-audit', 'closeout-sequence-40k'):
            submitted = answer.get('protected_inventory') if isinstance(answer, dict) else None
            candidates = submitted if isinstance(submitted, list) else []
            expected_items = gold.get('protected_inventory', [])
            expected_by_location = {
                (item.get('authority_id'), item.get('anchor')): item
                for item in expected_items if isinstance(item, dict)
            }
            by_location = {}
            malformed = []
            for item in candidates:
                if not isinstance(item, dict):
                    malformed.append('<invalid-item>')
                    continue
                location = (item.get('authority_id'), item.get('anchor'))
                if (not all(isinstance(part, str) and part for part in location)
                        or location not in expected_by_location):
                    malformed.append('#'.join(str(part) for part in location))
                    continue
                if location in by_location:
                    malformed.append('#'.join(location))
                by_location[location] = item

            lost = []
            missing_evidence = []
            extra = sorted(set(malformed))
            save_sequences = trace_check.get('authorized_save_sequences', [])
            save_sequence = max(save_sequences) if save_sequences else None
            for location, expected in expected_by_location.items():
                item_id = expected.get('id')
                observed = by_location.get(location)
                if not observed or any(observed.get(key) != expected.get(key) for key in (
                        'value', 'authority_id', 'anchor', 'attribution', 'uncertainty')):
                    lost.append(item_id)

                record = reference_records.get(expected.get('authority_id'))
                if (not isinstance(record, dict)
                        or not isinstance(record.get('content'), str)
                        or expected.get('value') not in record['content']
                        or expected.get('anchor') not in {
                            heading['anchor'] for heading in _headings_for_record(
                                expected.get('authority_id'), record, headings_cache)
                        }):
                    missing_from_records.append(item_id)

                supported = False
                citations = observed.get('evidence') if isinstance(observed, dict) else None
                for citation in citations if isinstance(citations, list) else []:
                    if not isinstance(citation, dict):
                        continue
                    sequence = citation.get('event_seq')
                    event = trace_check.get('events_by_seq', {}).get(sequence)
                    snapshot = trace_check.get('record_snapshots_by_seq', {}).get(sequence)
                    if (save_sequence is None or not isinstance(sequence, int)
                            or sequence <= save_sequence or not event or not event.get('ok')
                            or event.get('op') not in ('read_full', 'read_section')
                            or event.get('record_id') != expected.get('authority_id')
                            or citation.get('record_id') != expected.get('authority_id')
                            or citation.get('anchor') != expected.get('anchor')
                            or citation.get('version') != event.get('record_version')
                            or citation.get('response_sha256') != event.get('response_sha256')
                            or not isinstance(snapshot, dict)):
                        continue
                    response = event.get('response', {})
                    content = response.get('content', '')
                    if (expected.get('value') not in content
                            or expected.get('anchor') not in {
                                heading['anchor'] for heading in _headings_for_record(
                                    expected.get('authority_id'), snapshot, headings_cache)
                            }
                            or (event.get('op') == 'read_section'
                                and response.get('anchor') != expected.get('anchor'))):
                        continue
                    supported = True
                    break
                if not supported:
                    missing_evidence.append(item_id)
            protected = _check(
                not lost and not missing_from_records and not missing_evidence and not extra,
                {
                    'lost_or_changed_inventory_items': sorted(lost),
                    'missing_from_final_records': sorted(missing_from_records),
                    'missing_post_save_evidence': sorted(missing_evidence),
                    'unexpected_inventory_items': extra,
                },
            )
        else:
            for item in gold.get('protected_inventory', []):
                record = reference_records.get(item.get('authority_id'))
                if (not isinstance(record, dict)
                        or not isinstance(record.get('content'), str)
                        or item.get('value') not in record['content']
                        or item.get('anchor') not in {
                            heading['anchor'] for heading in _headings_for_record(
                                item.get('authority_id'), record, headings_cache)
                        }):
                    missing_from_records.append(item.get('id'))
            protected = _check(not missing_from_records, {
                'missing_from_final_records': sorted(missing_from_records),
            })
    pointer = _check(pointer_ok, {
        'missing_targets': missing_pointers,
        'targets_not_referenced_by_index': unreferenced_pointers,
        'stale_anchor_fallback_missing': missing_fallback,
    })
    return protected, pointer

def _staged_review_check(public, gold, reference_records, trace_check, answer, headings_cache):
    control = gold.get('staged_review')
    if not isinstance(control, dict):
        return _check(True, 'No staged candidate review is required.', applicable=False)

    record_id = control.get('record_id')
    record = reference_records.get(record_id)
    advertised = next((item for item in public.get('available_records', [])
                       if isinstance(item, dict) and item.get('id') == record_id), None)
    policy = control.get('review_policy')
    candidate = None
    parse_error = None
    if isinstance(record, dict):
        try:
            candidate = json.loads(record.get('content', ''))
        except (TypeError, json.JSONDecodeError) as error:
            parse_error = str(error)

    binding_ok = bool(
        advertised and record
        and all(advertised.get(key) == record.get(key)
                for key in ('id', 'path', 'version', 'kind'))
        and record.get('kind') == 'candidate'
        and public.get('staged_review_policy') == policy
        and policy == {'review_date': '2026-10-18', 'review_after_days': 180}
        and control.get('write_authorized') is False
        and isinstance(candidate, dict)
        and candidate.get('candidate_id') == 'staged-candidate-v1'
    )

    protected = {item.get('id'): item for item in gold.get('protected_inventory', [])
                 if isinstance(item, dict)}
    observed_items = candidate.get('fact_inventory', []) if isinstance(candidate, dict) else []
    observed = {item.get('id'): item for item in observed_items if isinstance(item, dict)}
    compared_fields = ('id', 'value', 'authority_id', 'anchor', 'attribution', 'uncertainty')
    lost_items = sorted(
        fact_id for fact_id, fact in protected.items()
        if fact_id not in observed
        or any(observed[fact_id].get(key) != fact.get(key) for key in compared_fields)
    )

    pointer_refs = (candidate.get('pointer_references', [])
                    if isinstance(candidate, dict) else [])
    references = {item.get('record_id'): item for item in pointer_refs
                  if isinstance(item, dict) and isinstance(item.get('record_id'), str)}
    unresolved = []
    for target in gold.get('pointer_targets', []):
        pointer_ref = references.get(target)
        target_record = reference_records.get(target)
        anchor = pointer_ref.get('anchor') if pointer_ref else None
        valid_anchors = ({item['anchor'] for item in _headings_for_record(
            target, target_record, headings_cache)} if isinstance(target_record, dict) else set())
        if not pointer_ref or not isinstance(anchor, str) or anchor not in valid_anchors:
            unresolved.append(f'{target}#{anchor or "missing-anchor"}')
    unresolved = sorted(unresolved)

    review_due = False
    review_date = None
    last_audit = candidate.get('last_verified_audit') if isinstance(candidate, dict) else None
    try:
        review_date = date.fromisoformat(policy['review_date'])
        last_date = date.fromisoformat(last_audit)
        interval = policy['review_after_days']
        review_due = (isinstance(interval, int) and not isinstance(interval, bool)
                      and interval >= 0 and (review_date - last_date).days >= interval)
    except (KeyError, TypeError, ValueError):
        binding_ok = False

    recovered = []
    for pointer in unresolved:
        target = pointer.split('#', 1)[0]
        fact = next((item for item in gold.get('required_facts', [])
                     if item.get('authority_id') == target), None)
        target_record = reference_records.get(target)
        valid_anchors = ({item['anchor'] for item in _headings_for_record(
            target, target_record, headings_cache)} if isinstance(target_record, dict) else set())
        if fact and fact.get('anchor') in valid_anchors:
            recovered.append({'record_id': target, 'anchor': fact['anchor']})

    if lost_items:
        expected_disposition = 'reject'
    elif unresolved:
        expected_disposition = 'recover'
    elif review_due:
        expected_disposition = 'review_only'
    else:
        expected_disposition = 'accept'
    expected = {
        'candidate_record_id': record_id,
        'disposition': expected_disposition,
        'lost_items': lost_items,
        'unresolved_pointers': unresolved,
        'recovered_pointers': recovered,
        'review_due': review_due,
        'write_authorized': False,
        'maintenance_action': 'none',
    }

    observed_answer = answer.get('audit_review') if isinstance(answer, dict) else None
    answer_matches = isinstance(observed_answer, dict) and all(
        observed_answer.get(key) == value for key, value in expected.items())
    evidence = observed_answer.get('evidence', {}) if isinstance(observed_answer, dict) else {}
    event = trace_check['events_by_seq'].get(
        evidence.get('event_seq')) if isinstance(evidence, dict) else None
    candidate_read = bool(
        isinstance(record, dict)
        and event and event.get('ok') and event.get('op') == 'read_full'
        and event.get('record_id') == record_id
        and event.get('response', {}).get('content') == record.get('content')
        and evidence.get('response_sha256') == event.get('response_sha256')
    )
    no_successful_write = not any(
        item.get('op') == SAVE_OP and item.get('ok')
        for item in trace_check['events_by_seq'].values()
    )
    passed = binding_ok and answer_matches and candidate_read and no_successful_write
    return _check(passed, {
        'expected': expected,
        'observed': observed_answer,
        'candidate_record_bound': binding_ok,
        'candidate_read_evidence_valid': candidate_read,
        'no_successful_write': no_successful_write,
        'candidate_parse_error': parse_error,
    })


def _update_checks(gold, initial_records, reference_records, trace_check, trace):
    authorization = gold.get('update_authorization')
    maintenance_authorization = gold.get('maintenance_authorization')
    expected = copy.deepcopy(initial_records)
    if isinstance(authorization, dict):
        record = expected.get(authorization.get('record_id'))
        if (record and record.get('version') == authorization.get('expected_version')
                and isinstance(authorization.get('append_text'), str)):
            record['content'] += authorization['append_text']
            record['version'] = authorization['new_version']
        else:
            expected = None

    stage_sequences = trace_check.get('maintenance_stage_sequences', [])
    maintenance_sequences = trace_check.get('authorized_maintenance_sequences', [])
    if maintenance_authorization:
        stage_valid = len(stage_sequences) == 1 and len(maintenance_sequences) == 1
        if stage_valid:
            promotion = trace_check['events_by_seq'][maintenance_sequences[0]]
            promotion_request = (promotion.get('request')
                                 if isinstance(promotion, dict)
                                 and isinstance(promotion.get('request'), dict) else {})
            stage_id = promotion_request.get('stage_id')
            staged = trace_check.get('staged_candidates', {}).get(stage_id)
            record = (expected.get(maintenance_authorization.get('record_id'))
                      if isinstance(expected, dict) else None)
            if (not staged or not record
                    or record.get('version') != maintenance_authorization.get('expected_version')):
                expected = None
            else:
                record['content'] = staged['candidate_content']
                record['version'] = maintenance_authorization['new_version']
                record['last_verified_audit'] = maintenance_authorization['completed_date']
        else:
            expected = None
    elif stage_sequences or maintenance_sequences:
        expected = None

    exact_final_state = expected is not None and expected == reference_records
    mismatched_records = []
    if expected is not None:
        mismatched_records = sorted(
            record_id for record_id in set(expected) | set(reference_records)
            if expected.get(record_id) != reference_records.get(record_id))
    else:
        mismatched_records = ['invalid-update-authorization']

    save_sequences = trace_check['authorized_save_sequences']
    save_count_ok = len(save_sequences) == (1 if authorization else 0)
    stage_count_ok = len(stage_sequences) == (1 if maintenance_authorization else 0)
    maintenance_count_ok = len(maintenance_sequences) == (
        1 if maintenance_authorization else 0)
    final_state = _check(
        exact_final_state and save_count_ok and stage_count_ok and maintenance_count_ok, {
        'mismatched_records': mismatched_records,
        'authorized_save_sequences': save_sequences,
        'required_save_count': 1 if authorization else 0,
        'maintenance_stage_sequences': stage_sequences,
        'authorized_maintenance_sequences': maintenance_sequences,
        'required_maintenance_stage_count': 1 if maintenance_authorization else 0,
        'required_maintenance_promotion_count': 1 if maintenance_authorization else 0,
        'maintenance_counts_valid': stage_count_ok and maintenance_count_ok,
    })

    if not authorization:
        readback = _check(True, 'No synthetic save is authorized for this scenario.',
                          applicable=False)
    else:
        save_seq = save_sequences[0] if len(save_sequences) == 1 else None
        readback_event = next((event for event in trace
                               if save_seq is not None
                               and event.get('seq', 0) > save_seq
                               and event.get('op') == 'read_full'
                               and event.get('ok')
                               and event.get('record_id') == authorization.get('record_id')
                               and event.get('record_version') == authorization.get('new_version')
                               and event.get('response', {}).get('version')
                               == authorization.get('new_version')),
                              None)
        target = reference_records.get(authorization.get('record_id'), {})
        readback_ok = bool(readback_event and readback_event.get('response', {}).get('content')
                           == target.get('content')
                           and readback_event.get('response', {}).get('content_sha256')
                           == _sha256_bytes(target.get('content', '').encode('utf-8')))
        readback = _check(readback_ok, {
            'authorized_save_sequence': save_seq,
            'readback_sequence': readback_event.get('seq') if readback_event else None,
            'record_id': authorization.get('record_id'),
        })
    return final_state, readback


def _maintenance_checks(gold, initial_records, reference_records, trace,
                        trace_check, maintenance_approval, headings_cache):
    authorization = gold.get('maintenance_authorization')
    stage_sequences = trace_check.get('maintenance_stage_sequences', [])
    promotion_sequences = trace_check.get('authorized_maintenance_sequences', [])
    stage_attempts = [event for event in trace if event.get('op') == STAGE_MAINTENANCE_OP]
    promotion_attempts = [event for event in trace if event.get('op') == PROMOTE_MAINTENANCE_OP]
    if not authorization:
        no_maintenance_calls = not stage_attempts and not promotion_attempts
        return (
            _check(no_maintenance_calls, {
                'stage_attempts': len(stage_attempts),
                'promotion_attempts': len(promotion_attempts),
            }, applicable=False),
            _check(True, 'No index maintenance is authorized for this scenario.',
                   applicable=False),
            _check(True, 'No index maintenance is authorized for this scenario.',
                   applicable=False),
        )

    approval = maintenance_approval if isinstance(maintenance_approval, dict) else {}
    stage = None
    promotion = None
    if len(stage_sequences) == 1:
        stage = trace_check.get('events_by_seq', {}).get(stage_sequences[0])
    if len(promotion_sequences) == 1:
        promotion = trace_check.get('events_by_seq', {}).get(promotion_sequences[0])
    promotion_request = (promotion.get('request')
                         if isinstance(promotion, dict)
                         and isinstance(promotion.get('request'), dict) else {})
    stage_id = promotion_request.get('stage_id')
    staged = trace_check.get('staged_candidates', {}).get(stage_id)
    approval_bound = bool(
        staged and approval.get('approved') is True
        and approval.get('evidence_kind') == 'out-of-band-scripted-consent'
        and approval.get('stage_id') == stage_id
        and approval.get('candidate_sha256') == staged.get('candidate_sha256')
        and approval.get('record_id') == authorization.get('record_id')
        and approval.get('expected_version') == authorization.get('expected_version')
        and approval.get('completed_date') == authorization.get('completed_date')
        and isinstance(promotion, dict)
        and approval.get('approval_id') == promotion_request.get('approval_id')
    )
    transition_passed = bool(
        len(stage_sequences) == 1 and len(promotion_sequences) == 1
        and approval_bound and isinstance(staged, dict)
        and staged.get('stage_sequence') < promotion.get('seq', 0)
    )
    transition = _check(transition_passed, {
        'stage_sequences': stage_sequences,
        'promotion_sequences': promotion_sequences,
        'approval_bound_to_staged_candidate': approval_bound,
        'approval_id': approval.get('approval_id'),
    })

    target_id = authorization['record_id']
    final_record = reference_records.get(target_id, {})
    if not isinstance(final_record, dict):
        final_record = {}
    readback_event = next((event for event in trace
                           if isinstance(promotion, dict)
                           and event.get('seq', 0) > promotion.get('seq', 0)
                           and event.get('op') == 'read_full'
                           and event.get('ok')
                           and event.get('record_id') == target_id
                           and event.get('record_version') == authorization.get('new_version')
                           and event.get('response', {}).get('version')
                           == authorization.get('new_version')),
                          None)
    readback_passed = bool(
        readback_event
        and readback_event.get('response', {}).get('content') == final_record.get('content')
        and readback_event.get('response', {}).get('content_sha256')
        == _sha256_bytes(final_record.get('content', '').encode('utf-8'))
        and readback_event.get('response', {}).get('last_verified_audit')
        == authorization.get('completed_date')
        and final_record.get('last_verified_audit') == authorization.get('completed_date')
    )
    readback = _check(readback_passed, {
        'promotion_sequence': promotion.get('seq') if isinstance(promotion, dict) else None,
        'readback_sequence': readback_event.get('seq') if readback_event else None,
        'record_id': target_id,
        'version': final_record.get('version'),
        'last_verified_audit': final_record.get('last_verified_audit'),
    })

    initial_index = initial_records.get(target_id, {})
    if not isinstance(initial_index, dict):
        initial_index = {}
    candidate_content = (staged.get('candidate_content') if isinstance(staged, dict) else None)
    candidate_bytes = len(candidate_content.encode('utf-8')) if isinstance(candidate_content, str) else None
    initial_bytes = len(initial_index.get('content', '').encode('utf-8'))
    required_bindings = sorted({
        f"{item.get('authority_id')}#{item.get('anchor')}"
        for item in gold.get('protected_inventory', [])
        if isinstance(item, dict)
    })
    index_text = final_record.get('content', '') if isinstance(final_record, dict) else ''
    missing_bindings = [pointer for pointer in required_bindings if pointer not in index_text]
    missing_targets = sorted(target for target in gold.get('pointer_targets', [])
                             if target not in index_text)
    missing_facts = []
    changed_authorities = []
    update_authorization = gold.get('update_authorization')
    save_attempts = [event for event in trace if event.get('op') == SAVE_OP]
    authorized_save_sequences = trace_check.get('authorized_save_sequences', [])
    expected_saved_record = None
    save_readback_sequence = None
    save_semantics_passed = not save_attempts and not isinstance(update_authorization, dict)
    update_target_id = None
    if isinstance(update_authorization, dict):
        update_target_id = update_authorization.get('record_id')
        original = initial_records.get(update_target_id)
        if (isinstance(original, dict)
                and isinstance(original.get('content'), str)
                and original.get('version') == update_authorization.get('expected_version')
                and isinstance(update_authorization.get('append_text'), str)
                and isinstance(update_authorization.get('new_version'), str)
                and update_authorization.get('new_version') != original.get('version')):
            expected_saved_record = copy.deepcopy(original)
            expected_saved_record['content'] += update_authorization['append_text']
            expected_saved_record['version'] = update_authorization['new_version']

        save_event = (trace_check.get('events_by_seq', {}).get(authorized_save_sequences[0])
                      if len(authorized_save_sequences) == 1 else None)
        save_readback_event = next((event for event in trace
                                    if isinstance(save_event, dict)
                                    and event.get('seq', 0) > save_event.get('seq', 0)
                                    and event.get('op') == 'read_full'
                                    and event.get('ok')
                                    and event.get('record_id') == update_target_id
                                    and event.get('record_version')
                                    == update_authorization.get('new_version')
                                    and event.get('response', {}).get('version')
                                    == update_authorization.get('new_version')),
                                   None)
        if (save_readback_event and isinstance(expected_saved_record, dict)
                and save_readback_event.get('response', {}).get('content')
                == expected_saved_record.get('content')
                and save_readback_event.get('response', {}).get('content_sha256')
                == _sha256_bytes(expected_saved_record.get('content', '').encode('utf-8'))):
            save_readback_sequence = save_readback_event.get('seq')
        save_semantics_passed = bool(
            len(save_attempts) == 1 and len(authorized_save_sequences) == 1
            and isinstance(expected_saved_record, dict)
            and reference_records.get(update_target_id) == expected_saved_record
            and save_readback_sequence is not None
        )

    for fact in gold.get('protected_inventory', []):
        if not isinstance(fact, dict):
            missing_facts.append('<invalid-item>')
            continue
        record_id = fact.get('authority_id')
        record = reference_records.get(record_id)
        if (not isinstance(record, dict)
                or fact.get('value') not in record.get('content', '')
                or fact.get('anchor') not in {
                    heading['anchor'] for heading in _headings_for_record(
                        record_id, record, headings_cache)
                }):
            missing_facts.append(fact.get('id'))
    for record_id, initial_record in initial_records.items():
        if record_id == target_id:
            continue
        expected_record = (expected_saved_record if record_id == update_target_id
                           and isinstance(expected_saved_record, dict)
                           else initial_record)
        if reference_records.get(record_id) != expected_record:
            changed_authorities.append(record_id)
    shorter = isinstance(candidate_bytes, int) and candidate_bytes < initial_bytes
    semantic_passed = bool(
        transition_passed and shorter and not missing_bindings and not missing_targets
        and not missing_facts and not changed_authorities and save_semantics_passed
    )
    semantic = _check(semantic_passed, {
        'initial_index_bytes': initial_bytes,
        'candidate_index_bytes': candidate_bytes,
        'candidate_is_shorter': shorter,
        'missing_pointer_bindings': missing_bindings,
        'missing_pointer_targets': missing_targets,
        'missing_or_changed_protected_facts': sorted(item for item in missing_facts if item),
        'changed_authoritative_records': sorted(set(changed_authorities)),
        'authorized_save_preserved_with_readback': save_semantics_passed,
        'save_readback_sequence': save_readback_sequence,
    })
    return transition, readback, semantic


def _maintenance_trigger_check(public, gold, initial_records):
    trigger = gold.get('maintenance_trigger')
    public_trigger = public.get('maintenance_trigger') if isinstance(public, dict) else None
    authorization = gold.get('maintenance_authorization')
    if trigger is None:
        passed = public_trigger is None and authorization is None
        return _check(passed, {
            'expected_trigger': None,
            'observed_trigger': public_trigger,
            'maintenance_authorization_present': authorization is not None,
        }, applicable=False)
    if not isinstance(trigger, dict):
        return _check(False, {
            'expected_trigger': 'controller maintenance trigger object',
            'observed_trigger': trigger,
        })

    record = initial_records.get('index') if isinstance(initial_records, dict) else None
    content = record.get('content') if isinstance(record, dict) else None
    last_audited = record.get('last_verified_audit') if isinstance(record, dict) else None
    threshold = trigger.get('threshold_kib')
    as_of_value = trigger.get('as_of')
    index_bytes = len(content.encode('utf-8')) if isinstance(content, str) else None
    threshold_valid = (isinstance(threshold, int) and not isinstance(threshold, bool)
                       and threshold in INDEX_TRIGGER_TREATMENTS_KIB)
    size_due = bool(
        threshold_valid and isinstance(index_bytes, int)
        and index_bytes > threshold * 1024
    )
    expected_reasons = []
    as_of = None
    try:
        as_of = date.fromisoformat(as_of_value)
    except (TypeError, ValueError, AttributeError):
        pass

    if size_due:
        expected_reasons.append('index-size')
    if not isinstance(last_audited, str):
        expected_reasons.append('missing-audit-date')
    else:
        try:
            audit_date = date.fromisoformat(last_audited)
        except (TypeError, ValueError, AttributeError):
            expected_reasons.append('invalid-audit-date')
        else:
            if as_of is None:
                expected_reasons.append('invalid-audit-date')
            elif (as_of - audit_date).days >= 180:
                expected_reasons.append('audit-interval')
    material_changes = trigger.get('material_changes')
    material_changes_valid = (isinstance(material_changes, int)
                              and not isinstance(material_changes, bool)
                              and material_changes >= 0)
    if (isinstance(material_changes, int) and not isinstance(material_changes, bool)
            and material_changes >= 25):
        expected_reasons.append('material-change-count')
    current_bytes = trigger.get('current_bytes')
    growth_baseline_bytes = trigger.get('growth_baseline_bytes')
    current_bytes_valid = (isinstance(current_bytes, int)
                           and not isinstance(current_bytes, bool)
                           and current_bytes >= 0 and current_bytes == index_bytes)
    growth_baseline_valid = (isinstance(growth_baseline_bytes, int)
                             and not isinstance(growth_baseline_bytes, bool)
                             and growth_baseline_bytes >= 0)
    growth_status = 'unavailable'
    if (growth_baseline_valid and growth_baseline_bytes > 0
            and current_bytes_valid):
        growth_status = 'measured'
        if ((current_bytes - growth_baseline_bytes) * 4 >= growth_baseline_bytes):
            expected_reasons.append('index-growth')
    expected_due = bool(expected_reasons)
    auth_matches = (
        (authorization is not None) == expected_due
        and (not expected_due or (
            isinstance(authorization, dict)
            and isinstance(record, dict)
            and authorization.get('record_id') == 'index'
            and authorization.get('expected_version') == record.get('version')
            and authorization.get('new_version') != record.get('version')
            and authorization.get('completed_date') == trigger.get('as_of')
        ))
    )
    derived_matches = bool(
        threshold_valid and as_of is not None
        and material_changes_valid and current_bytes_valid and growth_baseline_valid
        and trigger.get('index_bytes') == index_bytes
        and trigger.get('last_audited') == last_audited
        and trigger.get('as_of') == as_of_value
        and trigger.get('size_status') == 'measured'
        and trigger.get('size_triggered') == size_due
        and trigger.get('audit_due') == expected_due
        and trigger.get('reasons') == expected_reasons
        and trigger.get('growth_status') == growth_status
    )
    packet_matches = public_trigger == trigger
    return _check(bool(derived_matches and packet_matches and auth_matches), {
        'observed_trigger': public_trigger,
        'controller_trigger': trigger,
        'index_bytes': index_bytes,
        'threshold_kib': threshold,
        'expected_audit_due': expected_due,
        'expected_reasons': expected_reasons,
        'authorization_matches_trigger': auth_matches,
        'public_packet_matches_controller': packet_matches,
    })


def score_trial(public, gold, reference_records, trace, answer, usage=None,
                initial_records=None, maintenance_approval=None):
    """Score one retained attempt; cost cannot offset a critical recall failure."""
    reference_records = reference_records if isinstance(reference_records, dict) else {}
    trace = trace if isinstance(trace, list) else []
    initial_records = (initial_records if isinstance(initial_records, dict)
                       else reference_records)
    headings_cache = {}
    trace_result = _validate_trace(
        trace, initial_records, reference_records, gold, headings_cache,
        maintenance_approval=maintenance_approval)
    answer_checks = _answer_checks(answer or {}, gold, reference_records, trace_result, headings_cache)
    unauthorized = trace_result['unauthorized_event_sequences']
    protected, pointers = _audit_checks(gold, answer or {}, reference_records, trace, trace_result)
    staged_review = _staged_review_check(
        public, gold, reference_records, trace_result, answer or {}, headings_cache)
    final_state, write_readback = _update_checks(
        gold, initial_records, reference_records, trace_result, trace)
    maintenance_transition, maintenance_readback, maintenance_semantics = _maintenance_checks(
        gold, initial_records, reference_records, trace, trace_result,
        maintenance_approval, headings_cache)
    maintenance_trigger = _maintenance_trigger_check(public, gold, initial_records)
    observed_recovery_state_sha256 = sha256_json(initial_records)
    recovery_state = _check(
        isinstance(gold.get('recovery_state_sha256'), str)
        and gold['recovery_state_sha256'] == observed_recovery_state_sha256,
        {
            'expected_sha256': gold.get('recovery_state_sha256'),
            'observed_sha256': observed_recovery_state_sha256,
        },
    )
    checks = {
        'read_trace_integrity': _check(trace_result['passed'], trace_result['errors']),
        'complete_recall': answer_checks['complete_recall'],
        'evidence_support': answer_checks['evidence_support'],
        'unauthorized_attempts': _check(not unauthorized, {'event_sequences': unauthorized}),
        'protected_inventory': protected,
        'pointer_resolution': pointers,
        'staged_review': staged_review,
        'final_state_integrity': final_state,
        'write_readback': write_readback,
        'maintenance_transition': maintenance_transition,
        'maintenance_trigger': maintenance_trigger,
        'maintenance_readback': maintenance_readback,
        'maintenance_semantic_preservation': maintenance_semantics,
        'recovery_state': recovery_state,
    }
    read_events = [event for event in trace if event.get('op') in READ_OPS]
    write_events = [event for event in trace if event.get('op') == SAVE_OP]
    maintenance_stage_events = [event for event in trace
                                if event.get('op') == STAGE_MAINTENANCE_OP]
    maintenance_promotion_events = [event for event in trace
                                    if event.get('op') == PROMOTE_MAINTENANCE_OP]
    maintenance_events = maintenance_stage_events + maintenance_promotion_events
    successful = [event for event in read_events if event.get('ok')]
    counts = {op: sum(event.get('op') == op for event in read_events) for op in READ_OPS}
    bytes_by_op = {op: sum(event.get('returned_bytes', 0) for event in successful
                            if event.get('op') == op) for op in READ_OPS}
    topic_reads = sum(1 for event in successful
                      if reference_records.get(event.get('record_id'), {}).get('kind') == 'topic')
    fallback_reads = sum(1 for event in successful if event.get('op') == 'read_full'
                         and event.get('response', {}).get('reason') == 'fallback')
    index_bytes = len(reference_records.get('index', {}).get('content', '').encode('utf-8'))
    topic_sizes = {record_id: len(record.get('content', '').encode('utf-8'))
                   for record_id, record in reference_records.items()
                   if record.get('kind') == 'topic'}
    usage_measurement = _usage_measurement(usage)
    status = 'passed' if all(check['passed'] for check in checks.values()) else 'failed'
    return {
        'status': status,
        'scenario_id': gold.get('scenario_id', public.get('scenario_id')),
        'checks': checks,
        'measurements': {
            'sample_count': 1,
            'index_size_bytes': index_bytes,
            'topic_size_bytes': topic_sizes,
            'topic_size_bytes_total': sum(topic_sizes.values()),
            'reads': {
                'calls': len(read_events),
                'full_read_calls': counts['read_full'],
                'heading_map_calls': counts['read_heading_map'],
                'section_calls': counts['read_section'],
                'topic_read_calls': topic_reads,
                'fallback_full_reads': fallback_reads,
                'charged_bytes_by_operation': bytes_by_op,
                'charged_bytes_total': sum(bytes_by_op.values()),
                'section_savings_eligible': bool(counts['read_section'] and trace_result['section_events_valid']
                                                  and trace_result['passed']),
                'elapsed_ns_total': sum(event.get('elapsed_ns', 0) for event in read_events
                                        if isinstance(event.get('elapsed_ns'), int)),
                'timing_source': 'adapter monotonic per-operation elapsed time',
            },
            'token_usage': usage_measurement,
            'mutation_attempts': len(unauthorized),
            'audit_inventory_checked': bool(gold.get('audit_required')),
            'writes': {
                'save_attempts': len(write_events),
                'save_calls': sum(bool(event.get('ok')) for event in write_events),
                'save_request_bytes': sum(
                    event.get('request_bytes', 0) for event in write_events
                    if isinstance(event.get('request_bytes'), int)),
                'save_write_bytes': sum(
                    event.get('write_bytes', 0) for event in write_events
                    if event.get('ok') and isinstance(event.get('write_bytes'), int)),
                'save_returned_bytes': sum(
                    event.get('returned_bytes', 0) for event in write_events
                    if isinstance(event.get('returned_bytes'), int)),
                'maintenance_stage_attempts': len(maintenance_stage_events),
                'maintenance_stage_persisted_stages': len(
                    trace_result['maintenance_stage_sequences']),
                'maintenance_stage_retries': len(
                    trace_result['maintenance_stage_retry_sequences']),
                'maintenance_stage_calls': sum(
                    bool(event.get('ok')) for event in maintenance_stage_events),
                'maintenance_stage_request_bytes': sum(
                    event.get('request_bytes', 0) for event in maintenance_stage_events
                    if isinstance(event.get('request_bytes'), int)),
                'maintenance_stage_bytes': sum(
                    event.get('write_bytes', 0) for event in maintenance_stage_events
                    if event.get('ok') and isinstance(event.get('write_bytes'), int)),
                'maintenance_stage_returned_bytes': sum(
                    event.get('returned_bytes', 0) for event in maintenance_stage_events
                    if isinstance(event.get('returned_bytes'), int)),
                'maintenance_promote_attempts': len(maintenance_promotion_events),
                'maintenance_promote_calls': sum(
                    bool(event.get('ok')) for event in maintenance_promotion_events),
                'maintenance_promote_request_bytes': sum(
                    event.get('request_bytes', 0) for event in maintenance_promotion_events
                    if isinstance(event.get('request_bytes'), int)),
                'maintenance_promote_bytes': sum(
                    event.get('write_bytes', 0) for event in maintenance_promotion_events
                    if event.get('ok') and isinstance(event.get('write_bytes'), int)),
                'maintenance_promote_returned_bytes': sum(
                    event.get('returned_bytes', 0) for event in maintenance_promotion_events
                    if isinstance(event.get('returned_bytes'), int)),
                'maintenance_total_bytes': sum(
                    event.get('request_bytes', 0) + event.get('returned_bytes', 0)
                    + event.get('write_bytes', 0) for event in maintenance_events
                    if isinstance(event.get('request_bytes'), int)
                    and isinstance(event.get('returned_bytes'), int)
                    and isinstance(event.get('write_bytes'), int)),
                'elapsed_ns_total': sum(
                    event.get('elapsed_ns', 0) for event in write_events + maintenance_events
                    if isinstance(event.get('elapsed_ns'), int)),
            },
        },
        'limitations': [
            'Deterministic synthetic controls are not model behavior or live-provider evidence.',
            'Adapter per-operation time is not end-to-end session latency.',
            'Actual token use is unavailable unless supplied by provider-reported telemetry.',
        ],
    }
