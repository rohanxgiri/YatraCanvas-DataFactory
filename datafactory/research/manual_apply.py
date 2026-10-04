"""Selective, reviewed manual corrections through the immutable pack pipeline.

Proposal previews remain read-only. Approval is a separate explicit selection;
UNRESOLVED, merge and delete proposals cannot enter this apply operation.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from ..config.settings import get_settings
from ..models.place import Place
from ..pipeline.media_policy import media_policy
from ..pipeline.repair import human_field_locks
from ..utils.atomic import atomic_json
from ..utils.hashing import compute_sha256
from .export import snapshot, city_key, read_assurance
from .manual_resolution import preview_manual_changes, _field


def prepare_manual_apply(places, bundle, current_snapshot, approved_ids, *, locks=None):
    """Validate the entire proposal and return detached source records and full diff."""
    preview_manual_changes(places, bundle, current_snapshot)
    selected = list(approved_ids)
    proposals = {p['place_id']: p for p in bundle['proposals']}
    if not selected or len(set(selected)) != len(selected) or set(selected) - proposals.keys():
        raise ValueError('EXPLICIT_UNIQUE_APPROVED_IDS_REQUIRED')
    output = deepcopy(places)
    by_id = {p['id']: p for p in output}
    rows = []
    for pid in selected:
        item, place = proposals[pid], by_id[pid]
        if item['action'] not in {'KEEP', 'RENAME', 'DOWNGRADE'}:
            raise ValueError('UNRESOLVED_OR_DESTRUCTIVE_PROPOSAL_NOT_APPROVED')
        changes = deepcopy(item['changes'])
        review = item.get('tier_review', {})
        if (review.get('applied') is not False or
                review.get('current_tier') != place['tier'] or
                review.get('recommended_tier') not in {'core_destination', 'recommended', 'discovery', 'support'}):
            raise ValueError('EXPLICIT_REVIEWED_TIER_REQUIRED')
        changes['tier'] = review['recommended_tier']
        policy = item['media_policy_recommendation']
        before_policy = media_policy(place).value
        if policy['current'] != before_policy:
            raise ValueError('STALE_MEDIA_POLICY')
        fields = []
        for field, value in changes.items():
            before = _field(place, field)
            if before == value:
                continue
            human_fields = (locks or {}).get(pid, set())
            mapped = {'location.latitude': 'latitude', 'location.longitude': 'longitude'}.get(field, field)
            if (field in human_fields or mapped in human_fields or field.split('.')[0] in human_fields
                    or field == 'tier' and 'is_core' in human_fields):
                raise ValueError('HUMAN_FIELD_LOCK')
            parent = place
            parts = field.split('.')
            for key in parts[:-1]:
                parent = parent[key]
            parent[parts[-1]] = value
            fields.append({'field': field, 'before': before, 'after': deepcopy(value)})
        # Policy is derived by the existing model, never overridden by a sidecar.
        after_policy = media_policy(place).value
        if after_policy != policy['recommended']:
            raise ValueError('REVIEWED_TIER_POLICY_MISMATCH')
        if before_policy != after_policy:
            if 'media_policy' in (locks or {}).get(pid, set()):
                raise ValueError('HUMAN_FIELD_LOCK')
            fields.append({'field': 'media_policy', 'before': before_policy,
                           'after': after_policy, 'derived_from': 'tier'})
        Place.model_validate(place)
        rows.append({'place_id': pid, 'field_diff': fields, 'evidence': deepcopy(item['evidence']),
                     'reason': item['reason']})
    deferred = [p['place_id'] for p in bundle['proposals'] if p['place_id'] not in selected]
    return output, {'kind': 'reviewed_manual_apply', 'source_pack': bundle['source_pack'],
                    'source_snapshot': deepcopy(current_snapshot), 'approved_ids': selected,
                    'deferred_ids': deferred, 'rows': rows, 'paid_calls': 0,
                    'numeric_scores_changed': 0, 'media_assigned': 0, 'deleted': 0, 'merged': 0}


def apply_manual_changes(file: Path, approved_ids, diff_dir: Path, *, apply=False,
                         output_version='v3-research-jaipur-manual-01', settings=None):
    settings = settings or get_settings()
    if (not output_version or Path(output_version).name != output_version or '\\' in output_version or
            '/' in output_version or output_version in {'.', '..', 'v3'}):
        raise ValueError('NEW_SINGLE_DIRECTORY_VERSION_REQUIRED')
    bundle = json.loads(file.read_text(encoding='utf-8'))
    pack = (settings.releases_dir / bundle['source_pack']).resolve()
    if not pack.is_relative_to(settings.releases_dir.resolve()):
        raise ValueError('INVALID_SOURCE_PACK')
    if diff_dir.resolve().is_relative_to(settings.releases_dir.resolve()) or diff_dir.resolve().is_relative_to(settings.curated_dir.resolve()):
        raise ValueError('DIFF_CANNOT_MODIFY_RELEASE_OR_CURATION')
    from ..pipeline.validate import validate_release_package
    validate_release_package(pack)
    city = json.loads((pack / 'city.json').read_text(encoding='utf-8'))
    head_file = settings.data_dir / 'research/heads' / (city_key(city) + '.json')
    current = snapshot(pack)
    head = None
    if head_file.exists():
        head = json.loads(head_file.read_text(encoding='utf-8'))
        if head['output_pack'] != bundle['source_pack'] or head['snapshot'] != current:
            raise ValueError('STALE_SOURCE_HEAD')
    places = json.loads((pack / 'places.json').read_text(encoding='utf-8'))
    locks = human_field_locks(settings, city)
    updated, report = prepare_manual_apply(places, bundle, current, approved_ids, locks=locks)
    report.update(proposal_sha256=compute_sha256(file), dry_run=not apply,
                  reviewed_at=datetime.now(timezone.utc).isoformat(), output_version=output_version)
    atomic_json(diff_dir / 'safe_apply.diff.json', report)
    lines = ['# Reviewed safe-resolution diff', '', f"Source: {bundle['source_pack']}", '',
             '| Place | Field | Before | After |', '|---|---|---|---|']
    for row in report['rows']:
        for change in row['field_diff']:
            vals = [json.dumps(change[k], ensure_ascii=False).replace('|', '/') for k in ('before', 'after')]
            lines.append(f"| {row['place_id']} | {change['field']} | {vals[0]} | {vals[1]} |")
    lines += ['', 'Deferred unchanged: ' + ', '.join(report['deferred_ids']), '']
    (diff_dir / 'safe_apply.diff.md').write_text('\n'.join(lines), encoding='utf-8')
    if not apply:
        return report
    lock = settings.data_dir / 'research/.import-lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError('Another research import is active') from None
    try:
        # Recheck immediately before publication; never force a stale selection.
        if snapshot(pack) != current or compute_sha256(file) != report['proposal_sha256']:
            raise ValueError('STALE_SOURCE_SNAPSHOT')
        if head_file.exists() and json.loads(head_file.read_text(encoding='utf-8')) != head:
            raise ValueError('STALE_SOURCE_HEAD')
        if human_field_locks(settings, city) != locks:
            raise ValueError('HUMAN_FIELD_LOCK_CHANGED')
        assurance = read_assurance(pack)
        provenance = json.loads((pack / 'field_provenance.json').read_text(encoding='utf-8'))
        for row in report['rows']:
            for change in row['field_diff']:
                provenance.append({'place_id': row['place_id'], 'field': change['field'],
                    'before': change['before'], 'value': change['after'], 'source': 'reviewed_manual_resolution',
                    'input_sha256': report['proposal_sha256'], 'sources': row['evidence'],
                    'retrieved_at': report['reviewed_at'], 'source_pack': bundle['source_pack']})
        from ..pipeline.offline_export import export_offline
        from .importer import _write_head
        pack_report = {'assurance': assurance, 'field_provenance': provenance,
                       'ai_usage': {'paid_calls': 0, 'provider_calls': 0}, 'manual_resolution': report,
                       'fallback_strategy': json.loads((pack / 'manifest.json').read_text(encoding='utf-8')).get('fallback_presentation', {}).get('strategy', 'app')}
        output, after = export_offline(pack, pack.parent / output_version, updated, pack, pack_report)
        _write_head(settings, city, output)
        report.update(output_pack=str(output), usability_after={k: v for k, v in after.items() if k != 'places'})
        atomic_json(diff_dir / 'safe_apply.receipt.json', report)
        return report
    finally:
        lock.rmdir()
