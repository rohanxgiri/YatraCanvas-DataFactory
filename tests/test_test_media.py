"""Demo photo isolation, exact identity binding, and immutable offline exports."""
import copy
import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from datafactory.pipeline.test_media import (identity_hash, normalize_test_media, select_display_media,
                                            publish_test_media, valid_test_record)
from datafactory.pipeline.usability import usability
from datafactory.utils.atomic import atomic_json
from datafactory.utils.hashing import compute_sha256
from datafactory.research.export import snapshot, city_key
from test_research_handoff import research_pack, inventory
from test_local_intelligence import photo


def confirmation(place, file):
    return {'schema_version': '1.0', 'place_id': place['id'], 'identity_hash': identity_hash(place),
        'input_sha256': compute_sha256(file), 'source_name': 'Manually supplied test reference',
        'source_page': 'https://jaipurthrumylens.com/example/',
        'reference_image_url': 'https://jaipurthrumylens.com/example.jpg?w=720',
        'original_filename': file.name, 'confirmed_by': 'Human fixture reviewer',
        'identity_verified': True, 'real_photograph_confirmed': True, 'license_verified': False,
        'identity_evidence': [{'url': 'https://www.openstreetmap.org/way/987654', 'supports': 'Exact entity confirmed manually'}],
        'excluded_entities': ['Amber Fort Suraj Pol', 'Jorawar Singh Gate', 'Ajmeri Gate']}


@pytest.fixture
def test_record(tmp_path, sample_place):
    place = sample_place.model_dump(mode='json')
    place['tier'] = 'core_destination'
    place['images'] = {'primary': None, 'gallery': []}
    file = tmp_path / 'manual-photo.jpg'
    file.write_bytes(photo((640, 459), fmt='JPEG'))
    record = normalize_test_media(place, file, confirmation(place, file), tmp_path)
    return place, record, tmp_path


def test_decode_orientation_resize_and_thumbnail_are_local_and_never_upscaled(test_record):
    place, record, root = test_record
    assert valid_test_record(place, record, root)
    assert record['media_class'] == 'TEST_ONLY_REAL'
    assert not record['license_verified'] and not record['counts_toward_source_readiness']
    assert record['original_filename'] == 'manual-photo.jpg'
    assert record['image']['image_type'] == 'test_only_real'
    with Image.open(root / record['image']['local_path']) as primary:
        assert primary.format == 'WEBP' and primary.size == (640, 459)
    with Image.open(root / record['image']['thumbnail_path']) as thumbnail:
        assert thumbnail.format == 'WEBP' and max(thumbnail.size) == 400


def test_exif_orientation_is_applied_before_webp_output(tmp_path, sample_place):
    file = tmp_path / 'oriented.jpg'
    image = Image.new('RGB', (640, 459), 'orange')
    exif = Image.Exif()
    exif[274] = 6
    image.save(file, 'JPEG', exif=exif)
    place = sample_place.model_dump(mode='json')
    record = normalize_test_media(place, file, confirmation(place, file), tmp_path)
    with Image.open(tmp_path / record['image']['local_path']) as normalized:
        assert normalized.size == (459, 640)


def test_test_media_is_opt_in_and_does_not_certify_even_with_spoofed_assurance(test_record, sample_city_metadata):
    place, record, root = test_record
    assert select_display_media(place, {}, {place['id']: record}, root) is None
    selected = select_display_media(place, {}, {place['id']: record}, root, allow_test_media=True)
    assert selected['media_class'] == 'TEST_ONLY_REAL'
    assert not selected['counts_toward_source_readiness']
    place['images']['primary'] = selected['image']
    result = usability([place], sample_city_metadata.model_dump(mode='json'), root,
        {place['id']: {'media': {'verified': True}}})
    assert result['real_required_verified'] == 0 and result['REAL_REQUIRED_MEDIA_COVERAGE'] == 0
    assert not result['SOURCE_DATA_READY']
    assert 'CORE_MEDIA_UNRESOLVED' in result['places'][0]['critical_blockers']


def test_verified_photo_wins_over_test_media(test_record):
    place, record, root = test_record
    verified = {**record['image'], 'image_type': 'real', 'license': 'CC BY-SA 4.0',
        'license_url': 'https://creativecommons.org/licenses/by-sa/4.0/', 'author': 'Verified photographer'}
    place['images']['primary'] = verified
    # Rebind the manually confirmed image to the current unchanged identity.
    selected = select_display_media(place, {place['id']: {'media': {'verified': True}}},
        {place['id']: record}, root, allow_test_media=True)
    assert selected['media_class'] == 'VERIFIED_REAL'


def test_test_photo_precedes_ai_and_generic_fallback_in_demo_only(test_record):
    place, record, root = test_record
    base = {**record['image'], 'license': 'CC0', 'license_url': 'https://creativecommons.org/publicdomain/zero/1.0/', 'author': 'Artist'}
    place['images'] = {'primary': {**base, 'image_type': 'generic_fallback'},
                       'gallery': [{**base, 'image_type': 'ai_fallback'}]}
    assert select_display_media(place, {}, {place['id']: record}, root, allow_test_media=True)['media_class'] == 'TEST_ONLY_REAL'
    assert select_display_media(place, {}, {place['id']: record}, root)['media_class'] == 'AI_FALLBACK'
    place['images']['gallery'] = []
    assert select_display_media(place, {}, {}, root)['media_class'] == 'GENERIC_FALLBACK'


@pytest.mark.parametrize('wrong_name,wrong_id,lat,lon', [
    ('Suraj Pol at Amber Fort', 'amber_suraj', 26.986723, 75.851357),
    ('Jorawar Singh Gate', 'jorawar', 26.934, 75.830),
    ('Ajmeri Gate', 'ajmeri', 26.916, 75.818),
])
def test_wrong_gate_cannot_receive_confirmed_photo(test_record, wrong_name, wrong_id, lat, lon):
    place, record, root = test_record
    wrong = copy.deepcopy(place)
    wrong.update(id=wrong_id, name=wrong_name)
    wrong['location'].update(latitude=lat, longitude=lon)
    assert not valid_test_record(wrong, record, root)
    assert select_display_media(wrong, {}, {wrong_id: record}, root, allow_test_media=True) is None
    tampered = copy.deepcopy(record)
    tampered['place_id'] = wrong_id
    assert not valid_test_record(wrong, tampered, root)


@pytest.mark.parametrize('problem', ['bytes', 'identity', 'not_human_confirmed', 'license_verified', 'no_evidence', 'input_is_not_image'])
def test_unconfirmed_tampered_or_invalid_inputs_are_rejected_without_asset_writes(tmp_path, sample_place, problem):
    place = sample_place.model_dump(mode='json')
    file = tmp_path / 'photo.jpg'
    file.write_bytes(photo(fmt='JPEG'))
    review = confirmation(place, file)
    if problem == 'bytes':
        review['input_sha256'] = 'a' * 64
    elif problem == 'identity':
        review['identity_hash'] = 'b' * 64
    elif problem == 'not_human_confirmed':
        review['identity_verified'] = False
    elif problem == 'license_verified':
        review['license_verified'] = True
    elif problem == 'no_evidence':
        review['identity_evidence'] = []
    else:
        file.write_bytes(b'not an image')
        review['input_sha256'] = compute_sha256(file)
    with pytest.raises((ValueError, OSError)):
        normalize_test_media(place, file, review, tmp_path)
    assert not (tmp_path / 'media').exists()


def test_changed_local_asset_is_no_longer_eligible_for_demo(test_record):
    place, record, root = test_record
    (root / record['image']['local_path']).write_bytes(photo((640, 459), fmt='WEBP', variant=10))
    assert not valid_test_record(place, record, root)
    assert select_display_media(place, {}, {place['id']: record}, root, allow_test_media=True) is None


def test_publish_keeps_strict_records_head_and_history_and_exports_local_demo(research_pack):
    settings, source, place, *_ = research_pack
    atomic_json(source / 'field_provenance.json', [])
    city = json.loads((source / 'city.json').read_text())
    head_file = settings.data_dir / 'research/heads' / (city_key(city) + '.json')
    atomic_json(head_file, {'output_pack': source.relative_to(settings.releases_dir).as_posix(), 'snapshot': snapshot(source)})
    before, head_before = inventory(source), head_file.read_bytes()
    file = settings.project_root / 'supplied.jpg'
    file.write_bytes(photo((640, 459), fmt='JPEG'))
    review_file = settings.project_root / 'confirmed.json'
    atomic_json(review_file, confirmation(place, file))
    with pytest.raises(ValueError, match='EXPLICIT_ALLOW_TEST_MEDIA_REQUIRED'):
        publish_test_media(source, file, review_file, output_version='v3-demo', settings=settings)
    receipt = publish_test_media(source, file, review_file, output_version='v3-demo', allow_test_media=True, settings=settings)
    output = Path(receipt['output_pack'])
    assert inventory(source) == before and head_file.read_bytes() == head_before
    strict = json.loads((output / 'places.json').read_text())
    assert strict == [place] and strict[0]['images']['primary'] is None
    assert receipt['strict_metrics']['real_required_verified'] == 0
    assert receipt['demo_metrics']['demo_required_renderable_coverage'] == 100.0
    projected = json.loads((output / 'demo/places.json').read_text())
    image = projected[0]['images']['primary']
    assert image['image_type'] == 'test_only_real' and image['license'] == 'UNVERIFIED_TEST_ONLY'
    for relative in (image['local_path'], image['thumbnail_path']):
        assert (output / 'demo' / relative).is_file()
    from datafactory.pipeline.validate import validate_release_package
    validate_release_package(output)
    validate_release_package(output / 'demo')
    prior_output = inventory(output)
    another = publish_test_media(source, file, review_file, output_version='v3-demo', allow_test_media=True, settings=settings)
    assert Path(another['output_pack']) != output and inventory(output) == prior_output
    assert inventory(source) == before and head_file.read_bytes() == head_before


def test_cli_requires_explicit_test_media_flag(research_pack):
    from datafactory.cli import app
    settings, source, place, *_ = research_pack
    file, review = settings.project_root / 'supplied.jpg', settings.project_root / 'confirmation.json'
    file.write_bytes(photo(fmt='JPEG'))
    atomic_json(review, confirmation(place, file))
    result = CliRunner().invoke(app, ['test-media-import', '--image-file', str(file),
        '--confirmation-file', str(review), '--source-pack', str(source), '--output-version', 'v3-demo'])
    assert result.exit_code != 0 and 'EXPLICIT_ALLOW_TEST_MEDIA_REQUIRED' in result.output
