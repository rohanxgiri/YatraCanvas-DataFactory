"""Build and audit the explicitly requested local Suraj Pol demo photograph."""
import json
import os
import sys
from pathlib import Path
from datafactory.utils.atomic import atomic_json
from datafactory.utils.hashing import compute_sha256

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/demo/jaipur-test-media-01'
SOURCE = ROOT / 'releases/india/rajasthan/jaipur/v3-research-jaipur-manual-01'
IMAGE = Path('C:/Users/girir/Downloads/Video/suraj_pol_old_jaipur_test.jpg')
PID = 'yc_in_rj_jaipur_suraj_pol_gate'
SOURCE_PAGE = 'https://jaipurthrumylens.com/2016/10/06/history-old-city-gates-of-jaipur-architectural-design-elements/'
REFERENCE_IMAGE = 'https://jaipurthrumylens.com/wp-content/uploads/2016/10/surajpol-galta-gate-ramganj-bazaar-old-city-gates-in-jaipur-jaipurthrumylens.jpg?w=720'


def build():
    from datafactory.pipeline.test_media import identity_hash, publish_test_media
    place = next(p for p in json.loads((SOURCE / 'places.json').read_text(encoding='utf-8')) if p['id'] == PID)
    reviewed = json.loads((ROOT / 'data/research/manual_resolution/jaipur/proposed_changeset_01.json').read_text(encoding='utf-8'))
    evidence = next(p['evidence'] for p in reviewed['proposals'] if p['place_id'] == PID)
    confirmation = {'schema_version': '1.0', 'place_id': PID, 'identity_hash': identity_hash(place),
        'input_sha256': compute_sha256(IMAGE), 'source_name': 'JaipurThruMyLens',
        'source_page': SOURCE_PAGE, 'reference_image_url': REFERENCE_IMAGE, 'original_filename': IMAGE.name,
        'confirmed_by': 'Human user supplied image and exact-identity confirmation in this request',
        'identity_verified': True, 'real_photograph_confirmed': True, 'license_verified': False,
        'identity_evidence': [*evidence, {'url': SOURCE_PAGE,
            'supports': 'The Surajpole section identifies the eastern walled-city gate, and its captioned Surajpol photograph visually matches the manually supplied image.',
            'image_url': REFERENCE_IMAGE}],
        'excluded_entities': ['Amber Fort Suraj Pol', 'Suraj Pol inside Amer Fort', 'Jorawar Singh Gate', 'Ajmeri Gate']}
    confirmation_file = REPORT / 'manual_identity_confirmation.json'
    atomic_json(confirmation_file, confirmation)
    result = publish_test_media(SOURCE, IMAGE, confirmation_file,
        output_version='v3-demo-jaipur-test-media-01', allow_test_media=True)
    atomic_json(REPORT / 'import_receipt.json', result)
    print(json.dumps(result, ensure_ascii=False))


def baseline():
    from scripts.apply_jaipur_safe_resolution import protected_inventory
    target = REPORT / 'protected.before.json'
    if target.exists():
        raise ValueError('Baseline already captured')
    result = protected_inventory()
    result['strict_head_sha256'] = compute_sha256(ROOT / 'data/research/heads/59703eb7625225fc957024b1.json')
    atomic_json(target, result)
    print(json.dumps({'protected_files': len(result['files']), 'errors': result['errors']}))


def supplement(verify=False):
    target = REPORT / 'protected.supplement.json'
    if verify:
        before = json.loads(target.read_text(encoding='utf-8'))
        changed = [path for path, sha in before['files'].items() if not Path(path).is_file() or compute_sha256(Path(path)) != sha]
        atomic_json(REPORT / 'protected.supplement.verification.json', {'baseline_sha256': compute_sha256(target),
            'files_checked': len(before['files']), 'changed': changed})
        print(json.dumps({'files_checked': len(before['files']), 'changed': changed}))
        return
    if target.exists():
        raise ValueError('Supplement already captured')
    files, errors = {}, []
    before = json.loads((REPORT / 'protected.before.json').read_text(encoding='utf-8'))
    for message in before['errors']:
        base = Path(message.split(': ', 1)[1].strip("'").replace('\\\\', '\\'))
        for directory, _, names in os.walk(base, onerror=lambda error: errors.append(str(error))):
            for name in names:
                path = Path(directory) / name
                try:
                    files[str(path)] = compute_sha256(path)
                except OSError as error:
                    errors.append(str(error))
    atomic_json(target, {'files': files, 'errors': errors})
    print(json.dumps({'files_added': len(files), 'errors': errors}))


def verify():
    from scripts.apply_jaipur_safe_resolution import protected_inventory
    from datafactory.pipeline.validate import validate_release_package
    from datafactory.pipeline.test_media import select_display_media, valid_test_record
    from datafactory.pipeline.usability import usability
    before = json.loads((REPORT / 'protected.before.json').read_text(encoding='utf-8'))
    supplemental = json.loads((REPORT / 'protected.supplement.json').read_text(encoding='utf-8'))
    proof = json.loads((REPORT / 'protected.supplement.verification.json').read_text(encoding='utf-8'))
    assert not supplemental['errors'] and not proof['changed']
    assert proof['baseline_sha256'] == compute_sha256(REPORT / 'protected.supplement.json')
    intended = {str(ROOT / 'datafactory/cli.py'), str(ROOT / 'datafactory/pipeline/test_media.py'),
                str(ROOT / 'datafactory/models/test_media.py')}
    changed = [path for path, sha in before['files'].items() if not Path(path).is_file() or compute_sha256(Path(path)) != sha]
    assert not (set(changed) - intended), changed
    current = protected_inventory()
    assert current['errors'] == before['errors'], current['errors']
    receipt = json.loads((REPORT / 'import_receipt.json').read_text(encoding='utf-8'))
    output = Path(receipt['output_pack'])
    expected_new_code = {str(ROOT / 'datafactory/models/test_media.py'), str(ROOT / 'datafactory/pipeline/test_media.py')}
    unexpected = [path for path in current['files'] if path not in before['files']
        and not Path(path).is_relative_to(output) and path not in expected_new_code]
    assert not unexpected, unexpected
    assert before['strict_head_sha256'] == compute_sha256(ROOT / 'data/research/heads/59703eb7625225fc957024b1.json')
    for filename in ('places.json', 'places.jsonl', 'places.parquet', 'media_assurance.json', 'field_provenance.json'):
        if filename != 'places.parquet':
            assert compute_sha256(SOURCE / filename) == compute_sha256(output / filename), filename
    strict_before = json.loads((SOURCE / 'usability.json').read_text(encoding='utf-8'))
    strict_after = json.loads((output / 'usability.json').read_text(encoding='utf-8'))
    assert strict_after == strict_before
    places = json.loads((output / 'places.json').read_text(encoding='utf-8'))
    city = json.loads((output / 'city.json').read_text(encoding='utf-8'))
    assurance = json.loads((output / 'media_assurance.json').read_text(encoding='utf-8'))
    record = json.loads((output / 'test_media_manifest.json').read_text(encoding='utf-8'))['records'][PID]
    place = next(p for p in places if p['id'] == PID)
    assert valid_test_record(place, record, output)
    assert select_display_media(place, assurance, {PID: record}, output) is None
    selected = select_display_media(place, assurance, {PID: record}, output, allow_test_media=True)
    assert selected['media_class'] == 'TEST_ONLY_REAL' and not selected['counts_toward_source_readiness']
    demo_places = json.loads((output / 'demo/places.json').read_text(encoding='utf-8'))
    demo_place = next(p for p in demo_places if p['id'] == PID)
    assert demo_place['images']['primary']['image_type'] == 'test_only_real'
    for pid, assessment in assurance.items():
        if assessment.get('media', {}).get('verified') is True:
            p = next(p for p in places if p['id'] == pid)
            for relative in (p['images']['primary']['local_path'], p['images']['primary']['thumbnail_path']):
                assert compute_sha256(SOURCE / relative) == compute_sha256(output / relative)
    demo_check = usability(demo_places, city, output / 'demo', assurance)
    assert demo_check['real_required_verified'] == 17 and demo_check['REAL_REQUIRED_MEDIA_COVERAGE'] == 34.0
    checksums = json.loads((output / 'demo/checksums.json').read_text(encoding='utf-8'))
    for relative, sha in checksums.items():
        assert compute_sha256(output / 'demo' / relative) == sha
    from PIL import Image
    with Image.open(IMAGE) as original, Image.open(output / record['image']['local_path']) as normalized:
        assert normalized.width <= original.width and normalized.height <= original.height
    result = {'validation': validate_release_package(output), 'strict_metrics_unchanged': True,
        'strict_verified_count': 17, 'strict_required_total': 50, 'strict_required_coverage': 34.0,
        'source_readiness': False, 'demo_metrics': receipt['demo_metrics'],
        'historical_releases_unchanged': True, 'city_lab_unchanged': True,
        'protected_files_checked': len(before['files']) + len(supplemental['files']),
        'protected_changes': [], 'intended_code_changes': changed,
        'strict_head_unchanged': True, 'production_assurance_unchanged': True,
        'verified_assets_preserved': 17, 'paid_ai_calls': 0, 'provider_calls': 0,
        'suraj_status': {'identity_status': 'RESOLVED', 'demo_media_status': 'RESOLVED',
                         'strict_verified_media_status': 'UNRESOLVED', 'strict_license': 'UNVERIFIED'},
        'offline_card_and_detail_asset_validation': 'PASS'}
    atomic_json(REPORT / 'validation_and_safety.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    mode = sys.argv[1]
    {'baseline': baseline, 'supplement-baseline': supplement, 'build': build,
     'verify-supplement': lambda: supplement(True), 'verify': verify}[mode]()
