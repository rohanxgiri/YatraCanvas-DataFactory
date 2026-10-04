import copy
import json
from pathlib import Path

import pytest

from datafactory.research.manual_apply import prepare_manual_apply, apply_manual_changes
from datafactory.research.manual_resolution import record_fingerprint
from datafactory.research.export import snapshot, export_research
from datafactory.pipeline.media_policy import media_policy
from datafactory.utils.atomic import atomic_json
from test_research_handoff import research_pack, inventory


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'releases/india/rajasthan/jaipur/v3-research-jaipur-images-03'
APPROVED = ['yc_in_rj_jaipur_' + name for name in ('suraj_pol_gate', 'india_gate', 'rooftop_view_stairs')]


@pytest.fixture
def reviewed_jaipur():
    places = json.loads((SOURCE / 'places.json').read_text(encoding='utf-8'))
    bundle = json.loads((ROOT / 'data/research/manual_resolution/jaipur/proposed_changeset_01.json').read_text(encoding='utf-8'))
    return places, bundle, snapshot(SOURCE)


def test_reviewed_subset_preserves_scores_ids_media_and_unselected_records(reviewed_jaipur):
    original = copy.deepcopy(reviewed_jaipur)
    places, bundle, signature = reviewed_jaipur
    result, diff = prepare_manual_apply(places, bundle, signature, APPROVED)
    assert reviewed_jaipur == original
    before, after = ({p['id']: p for p in rows} for rows in (places, result))
    assert before.keys() == after.keys()
    assert set(diff['approved_ids']) == set(APPROVED)
    for pid in before:
        assert before[pid]['images'] == after[pid]['images']
        for field in ('travel_relevance_score', 'prominence_score', 'location', 'sources', 'provenance_records'):
            assert before[pid][field] == after[pid][field]
        if pid not in APPROVED:
            assert before[pid] == after[pid]
    assert after[APPROVED[0]]['external_ids'] == before[APPROVED[0]]['external_ids']
    assert after[APPROVED[2]]['external_ids']['osm_id'] == 'node/11533709370'


@pytest.mark.parametrize('name', ['jain_mandir', 'haveli', 'elephant_riding'])
def test_deferred_proposals_remain_untouched(reviewed_jaipur, name):
    places, bundle, signature = reviewed_jaipur
    result, diff = prepare_manual_apply(places, bundle, signature, APPROVED)
    pid = 'yc_in_rj_jaipur_' + name
    assert next(p for p in places if p['id'] == pid) == next(p for p in result if p['id'] == pid)
    assert pid in diff['deferred_ids']


def test_required_denominator_is_recomputed_by_normal_policy(reviewed_jaipur):
    result, _ = prepare_manual_apply(*reviewed_jaipur, APPROVED)
    assert sum(media_policy(p).value == 'REAL_REQUIRED' for p in reviewed_jaipur[0]) == 52
    assert sum(media_policy(p).value == 'REAL_REQUIRED' for p in result) == 50
    by_id = {p['id']: p for p in result}
    assert media_policy(by_id[APPROVED[0]]).value == 'REAL_REQUIRED'
    assert media_policy(by_id[APPROVED[1]]).value == 'REAL_PREFERRED'
    assert media_policy(by_id[APPROVED[2]]).value == 'FALLBACK_ALLOWED'


@pytest.mark.parametrize('problem', ['snapshot', 'record', 'duplicate', 'unknown', 'unresolved', 'policy', 'tier', 'lock', 'numeric_field', 'media'])
def test_unsafe_or_stale_selection_fails_without_mutation(reviewed_jaipur, problem):
    places, bundle, signature = reviewed_jaipur
    ids, locks = APPROVED.copy(), {}
    if problem == 'snapshot':
        signature['places.json'] = 'stale'
    elif problem == 'record':
        places[0]['description'] = 'changed after review'
        # Ensure a reviewed record is the one made stale.
        next(p for p in places if p['id'] == APPROVED[0])['name'] = 'changed'
    elif problem == 'duplicate':
        ids.append(ids[0])
    elif problem == 'unknown':
        ids.append('unknown')
    elif problem == 'unresolved':
        ids.append('yc_in_rj_jaipur_elephant_riding')
    elif problem == 'policy':
        bundle['proposals'][0]['media_policy_recommendation']['recommended'] = 'REAL_PREFERRED'
    elif problem == 'tier':
        bundle['proposals'][0]['tier_review']['current_tier'] = 'discovery'
    elif problem == 'lock':
        locks[APPROVED[0]] = {'alternate_names'}
    elif problem == 'numeric_field':
        bundle['proposals'][0]['changes']['prominence_score'] = 0.2
    elif problem == 'media':
        bundle['proposals'][0]['changes']['images.primary'] = None
    before = copy.deepcopy((places, bundle, signature))
    with pytest.raises(ValueError):
        prepare_manual_apply(places, bundle, signature, ids, locks=locks)
    assert (places, bundle, signature) == before


def test_apply_publishes_new_immutable_exports_and_registered_fresh_tasks(research_pack):
    settings, pack, place, _, _, _ = research_pack
    # The real source has this sidecar; keep the synthetic fixture faithful.
    atomic_json(pack / 'field_provenance.json', [])
    item = {'place_id': place['id'], 'action': 'DOWNGRADE', 'before_sha256': record_fingerprint(place),
        'changes': {'name': 'Reviewed local landmark'}, 'reason': 'Reviewed synthetic local identity.',
        'evidence': [{'url': 'https://www.openstreetmap.org/way/987654', 'supports': 'Exact object'}],
        'media_policy_recommendation': {'current': 'REAL_REQUIRED', 'recommended': 'REAL_PREFERRED', 'reason': 'Non-core', 'applied': False},
        'tier_review': {'current_tier': 'core_destination', 'recommended_tier': 'recommended', 'applied': False}}
    bundle = {'kind': 'manual_identity_proposals', 'schema_version': '1.0', 'apply_ready': False,
              'source_pack': pack.relative_to(settings.releases_dir).as_posix(),
              'source_snapshot': snapshot(pack), 'proposals': [item]}
    proposal = settings.project_root / 'review.json'
    atomic_json(proposal, bundle)
    before = inventory(pack)
    dry = apply_manual_changes(proposal, [place['id']], settings.project_root / 'dry', settings=settings)
    assert dry['dry_run'] and inventory(pack) == before
    receipt = apply_manual_changes(proposal, [place['id']], settings.project_root / 'apply', apply=True, settings=settings)
    output = Path(receipt['output_pack'])
    assert inventory(pack) == before
    assert output != pack
    published = json.loads((output / 'places.json').read_text(encoding='utf-8'))
    assert published[0]['name'] == 'Reviewed local landmark'
    assert receipt['usability_after']['real_required_total'] == 0
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['counts']['by_tier'] == {'recommended': 1}
    handoff = export_research(output, settings.project_root / 'fresh', include_optional=True, settings=settings)
    registered = json.loads((settings.data_dir / 'research/handoffs' / (handoff['handoff_id'] + '.json')).read_text())
    assert registered['snapshot'] == snapshot(output)
    assert registered['source_pack'].endswith(output.name)
    protected = inventory(output)
    with pytest.raises(ValueError, match='STALE_SOURCE_HEAD'):
        apply_manual_changes(proposal, [place['id']], settings.project_root / 'again', apply=True, settings=settings)
    assert inventory(pack) == before and inventory(output) == protected


@pytest.mark.parametrize('reviewed,other_hold,blocked,state', [
    (False, False, False, 'MANUAL_REVIEW'),
    (True, False, False, 'NEW_RESEARCH_REQUIRED'),
    (True, True, False, 'MANUAL_REVIEW'),
    (True, False, True, 'MANUAL_REVIEW'),
])
def test_reviewed_identity_duplicate_requests_fresh_photo_without_waiving_holds(
        research_pack, reviewed, other_hold, blocked, state):
    from datafactory.research.resolution import resolve_media_tasks
    from datafactory.research.export import make_tasks
    from test_local_intelligence import candidate
    settings, pack, place, *_ = research_pack
    codes = ['DUPLICATE_IMAGE'] + (['HUMAN_FIELD_LOCK'] if other_hold else [])
    assurance = {place['id']: {'identity_blocker': blocked, 'media': {'verified': False, 'candidates': [
        {'action': 'REVIEW', 'reason_codes': codes, 'candidate': candidate().model_dump()}]}}}
    atomic_json(pack / 'media_assurance.json', assurance)
    if reviewed:
        atomic_json(pack / 'ai_repair.json', {'manual_resolution': {'kind': 'reviewed_manual_apply',
            'approved_ids': [place['id']], 'rows': [{'place_id': place['id'], 'field_diff': [
                {'field': 'alternate_names', 'before': [], 'after': ['Reviewed identity']}]}]}})
    city = json.loads((pack / 'city.json').read_text())
    tasks = make_tasks([place], city, pack, assurance)
    before = inventory(pack)
    row = resolve_media_tasks(pack, tasks, settings=settings)[0]
    assert row['resolution_state'] == state
    assert inventory(pack) == before
    assert assurance[place['id']]['media']['verified'] is False
    if state == 'NEW_RESEARCH_REQUIRED':
        assert row['alternate_image_required']
        assert row['resolution_reason'] == 'REVIEWED_IDENTITY_REQUIRES_FRESH_RESEARCH'


def test_jain_coordinate_identity_conflict_retains_explicit_pin_review_flag():
    from datafactory.research.resolution import classify_media
    task = {'type': 'REAL_PRIMARY_IMAGE', 'known_evidence': {'media_policy': 'REAL_REQUIRED'}}
    research = {'status': 'CONFLICT', 'result': {},
        'research_notes': 'The alias conflicts with the central-Jaipur coordinates. Resolve place identity before selecting a primary image.'}
    row = classify_media(task, research)
    assert row['resolution_state'] == 'MANUAL_REVIEW'
    assert {'IDENTITY_REVIEW', 'PIN_REVIEW_REQUIRED'} <= set(row['review_flags'])
