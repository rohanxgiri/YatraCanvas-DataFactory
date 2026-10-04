"""Opt-in local demo media, isolated from the strict production-media importer."""
from copy import deepcopy
from datetime import datetime, timezone
from enum import Enum
import io
import json
import shutil
import uuid
from pathlib import Path
from html import escape

from PIL import Image, ImageOps

from ..ai.router import digest
from ..config.settings import get_settings
from ..models.test_media import ManualTestMediaConfirmation, TestOnlyMediaRecord
from ..models.place import Place
from ..models.city import CityMetadata
from ..utils.atomic import atomic_json
from ..utils.hashing import compute_sha256
from .identity_assurance import compact_identity
from .media_assurance import local_asset, license_allowed, media_signature
from .media_policy import media_policy


class DisplayMediaClass(str, Enum):
    VERIFIED_REAL = 'VERIFIED_REAL'
    TEST_ONLY_REAL = 'TEST_ONLY_REAL'
    AI_FALLBACK = 'AI_FALLBACK'
    GENERIC_FALLBACK = 'GENERIC_FALLBACK'


def identity_hash(place):
    return digest(compact_identity(place))


def validate_confirmation(place, file, confirmation):
    confirmation = ManualTestMediaConfirmation.model_validate(confirmation)
    if (confirmation.place_id != place['id'] or confirmation.identity_hash != identity_hash(place)):
        raise ValueError('TEST_MEDIA_EXACT_IDENTITY_MISMATCH')
    if file.name != confirmation.original_filename or compute_sha256(file) != confirmation.input_sha256:
        raise ValueError('TEST_MEDIA_INPUT_MISMATCH')
    from ..research.quality import public_source
    from .media_assurance import public_url
    if not public_source(confirmation.source_page) or not public_url(confirmation.reference_image_url):
        raise ValueError('PUBLIC_REFERENCE_REQUIRED')
    if any(not public_source(e.get('url')) or not e.get('supports') for e in confirmation.identity_evidence):
        raise ValueError('IDENTITY_EVIDENCE_REQUIRED')
    return confirmation


def normalize_test_media(place, file, confirmation, output_root):
    """Decode/re-encode only; no license acceptance, network, or AI invocation."""
    file, output_root = Path(file), Path(output_root)
    if file.stat().st_size > 20_000_000:
        raise ValueError('TEST_IMAGE_BYTES_EXCEEDED')
    attestation = validate_confirmation(place, file, confirmation)
    content = file.read_bytes()
    with Image.open(io.BytesIO(content)) as check:
        if check.format not in {'JPEG', 'PNG', 'WEBP'} or check.width * check.height > 40_000_000:
            raise ValueError('TEST_IMAGE_FORMAT_OR_DIMENSIONS_INVALID')
        check.verify()
    with Image.open(io.BytesIO(content)) as decoded:
        decoded.load()
        image = ImageOps.exif_transpose(decoded).convert('RGB')
        image.thumbnail((1280, 1280))  # Pillow never enlarges a smaller input.
        thumbnail = image.copy()
        thumbnail.thumbnail((400, 400))
    relative = Path('media/test_only') / place['id'] / attestation.input_sha256[:16]
    destination = output_root / relative
    if not destination.resolve().is_relative_to(output_root.resolve()):
        raise ValueError('INVALID_TEST_MEDIA_PATH')
    if destination.exists():
        raise ValueError('TEST_MEDIA_BUNDLE_ALREADY_EXISTS')
    destination.mkdir(parents=True)
    image.save(destination / 'primary.webp', 'WEBP', quality=88)
    thumbnail.save(destination / 'thumbnail.webp', 'WEBP', quality=85)
    now = datetime.now(timezone.utc).isoformat()
    record = TestOnlyMediaRecord(
        **{k: v for k, v in attestation.model_dump().items() if k not in {'schema_version', 'real_photograph_confirmed'}},
        imported_at=now, primary_sha256=compute_sha256(destination / 'primary.webp'),
        thumbnail_sha256=compute_sha256(destination / 'thumbnail.webp'),
        image={'image_type': 'test_only_real', 'source': attestation.source_name,
            'source_page': attestation.source_page, 'original_file': attestation.original_filename,
            'author': None, 'license': 'UNVERIFIED_TEST_ONLY', 'license_url': None,
            'attribution': f'{attestation.source_name} — manually supplied; local testing only; license unverified',
            'width': image.width, 'height': image.height, 'match_method': 'manual_exact_identity_test_only',
            'match_confidence': 0.0, 'downloaded_at': now,
            'local_path': (relative / 'primary.webp').as_posix(),
            'thumbnail_path': (relative / 'thumbnail.webp').as_posix(),
            'content_sha256': compute_sha256(destination / 'primary.webp')})
    result = record.model_dump(mode='json')
    atomic_json(destination / 'metadata.json', result)
    return result


def _renderable(image, root):
    if not image:
        return False
    for key in ('local_path', 'thumbnail_path'):
        path = local_asset(root, image.get(key))
        if path is None:
            return False
        try:
            with Image.open(path) as decoded:
                decoded.verify()
        except (OSError, ValueError):
            return False
    return True


def valid_test_record(place, raw, root):
    try:
        record = TestOnlyMediaRecord.model_validate(raw)
        image = record.image.model_dump(mode='json')
        return bool(record.place_id == place['id'] and record.identity_hash == identity_hash(place)
            and image['image_type'] == 'test_only_real' and image['license'] == 'UNVERIFIED_TEST_ONLY'
            and image['match_method'] == 'manual_exact_identity_test_only' and _renderable(image, root)
            and compute_sha256(local_asset(root, image['local_path'])) == record.primary_sha256
            and compute_sha256(local_asset(root, image['thumbnail_path'])) == record.thumbnail_sha256)
    except (ValueError, TypeError, OSError):
        return False


def select_display_media(place, assurance, test_records, root, *, allow_test_media=False):
    """Strict by default. Enabling demo media never changes verification state."""
    image = place.get('images', {}).get('primary')
    proof = assurance.get(place['id'], {}).get('media', {})
    if (image and image.get('image_type', 'real') == 'real' and proof.get('verified') is True
            and license_allowed(image.get('license', '')) and image.get('license_url')
            and image.get('author') and image.get('attribution') and image.get('source_page')
            and _renderable(image, root)
            and (not proof.get('identity_hash') or proof['identity_hash'] == identity_hash(place))
            and (not proof.get('verification_hash') or proof['verification_hash'] == media_signature(root, image))):
        return {'media_class': DisplayMediaClass.VERIFIED_REAL.value, 'image': deepcopy(image),
                'counts_toward_source_readiness': True}
    record = test_records.get(place['id'])
    if allow_test_media and record and valid_test_record(place, record, root):
        return {'media_class': DisplayMediaClass.TEST_ONLY_REAL.value, 'image': deepcopy(record['image']),
                'counts_toward_source_readiness': False}
    fallbacks = [i for i in [image, *place.get('images', {}).get('gallery', [])] if i and
        i.get('image_type') in {'fallback', 'ai_fallback', 'generic_fallback'} and
        license_allowed(i.get('license', '')) and i.get('author') and i.get('attribution')
        and i.get('license_url') and i.get('source_page') and _renderable(i, root)]
    fallbacks.sort(key=lambda i: i.get('image_type') != 'ai_fallback')
    if fallbacks:
        fallback = fallbacks[0]
        return {'media_class': (DisplayMediaClass.AI_FALLBACK if fallback['image_type'] == 'ai_fallback'
                else DisplayMediaClass.GENERIC_FALLBACK).value, 'image': deepcopy(fallback),
                'counts_toward_source_readiness': False}
    return None


def export_test_media_projection(pack, places, city, assurance, records, work_root):
    """Add isolated assets and an explicit demo projection to a staged new pack."""
    records = {pid: TestOnlyMediaRecord.model_validate(row).model_dump(mode='json') for pid, row in records.items()}
    by_id = {p['id']: p for p in places}
    for pid, row in records.items():
        if pid not in by_id or not valid_test_record(by_id[pid], row, work_root):
            raise ValueError('INVALID_OR_WRONG_ENTITY_TEST_MEDIA')
        for key in ('local_path', 'thumbnail_path'):
            relative = row['image'][key]
            source = local_asset(work_root, relative)
            target = (pack / relative).resolve()
            if not target.is_relative_to(pack.resolve()):
                raise ValueError('INVALID_TEST_MEDIA_PATH')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        atomic_json(pack / Path(row['image']['local_path']).parent / 'metadata.json', row)
    atomic_json(pack / 'test_media_manifest.json', {'schema_version': '1.0', 'default_enabled': False,
        'usage_scope': 'local_testing_only', 'counts_toward_source_readiness': False, 'records': records})
    atomic_json(pack / 'test_media_record.schema.json', TestOnlyMediaRecord.model_json_schema())
    atomic_json(pack / 'manual_test_media_confirmation.schema.json', ManualTestMediaConfirmation.model_json_schema())
    sources = json.loads((pack / 'source_manifest.json').read_text(encoding='utf-8'))
    sources.setdefault('sources', {})['test_only_external_media'] = {
        'source': 'Manually supplied external test photographs', 'license': 'UNVERIFIED_TEST_ONLY',
        'license_verified': False, 'usage_scope': 'local_testing_only',
        'role': 'Opt-in demo photographs; exact identity confirmed manually; excluded from source readiness',
        'source_pages': sorted({r['source_page'] for r in records.values()})}
    atomic_json(pack / 'source_manifest.json', sources)
    licensing = json.loads((pack / 'license_manifest.json').read_text(encoding='utf-8'))
    licensing['test_only_media'] = {'license_verified': False, 'usage_scope': 'local_testing_only',
        'production_reuse_authorized': False, 'manifest': 'test_media_manifest.json'}
    atomic_json(pack / 'license_manifest.json', licensing)
    demo = pack / 'demo'
    demo.mkdir(exist_ok=True)
    projected, selections = [], {}
    for place in places:
        selection = select_display_media(place, assurance, records, pack, allow_test_media=True)
        projection = deepcopy(place)
        projection['images'] = {'primary': selection['image'] if selection else None, 'gallery': []}
        projected.append(projection)
        if selection:
            selections[place['id']] = selection
            for key in ('local_path', 'thumbnail_path'):
                relative = selection['image'][key]
                target = (demo / relative).resolve()
                if not target.is_relative_to(demo.resolve()):
                    raise ValueError('INVALID_DEMO_ASSET_PATH')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(pack / relative, target)
    from ..exporters.json_exporter import export_places_json, export_places_jsonl, export_city_json
    from ..exporters.parquet_exporter import export_places_parquet
    from ..exporters.sqlite_exporter import export_sqlite
    parsed = [Place.model_validate(p) for p in projected]
    meta = CityMetadata.model_validate(city)
    export_places_json(parsed, demo / 'places.json')
    export_places_jsonl(parsed, demo / 'places.jsonl')
    export_city_json(meta, demo / 'city.json')
    export_places_parquet(parsed, demo / 'places.parquet')
    export_sqlite(meta, parsed, demo / 'yatracanvas.db')
    required = [p for p in places if media_policy(p).value == 'REAL_REQUIRED']
    required_display = sum(p['id'] in selections for p in required)
    metrics = {'published': len(places), 'demo_renderable_count': len(selections),
        'demo_renderable_media_coverage': round(len(selections) / len(places) * 100, 2) if places else 100.0,
        'required_total': len(required), 'demo_required_renderable_count': required_display,
        'demo_required_renderable_coverage': round(required_display / len(required) * 100, 2) if required else 100.0,
        'test_only_renderable_count': sum(s['media_class'] == 'TEST_ONLY_REAL' for s in selections.values()),
        'not_source_readiness_metrics': True}
    atomic_json(demo / 'media_selection.json', {'allow_test_media': True, 'production_release': False,
        'selections': selections, 'metrics': metrics})
    atomic_json(demo / 'test_media_manifest.json', {'schema_version': '1.0', 'records': records,
        'usage_scope': 'local_testing_only', 'counts_toward_source_readiness': False})
    for filename in ('source_manifest.json', 'license_manifest.json', 'media_assurance.json', 'field_provenance.json'):
        shutil.copyfile(pack / filename, demo / filename)
    from .usability import usability
    demo_usability = usability(projected, city, demo, assurance)
    atomic_json(demo / 'usability.json', demo_usability)
    image_manifest = {p.id: p.images.model_dump(mode='json') for p in parsed if p.images.primary}
    atomic_json(demo / 'image_manifest.json', image_manifest)
    atomic_json(demo / 'images_manifest.json', image_manifest)
    demo_manifest = json.loads((pack / 'manifest.json').read_text(encoding='utf-8'))
    demo_manifest.update(usage_scope='local_testing_only', allow_test_media=True,
        production_release=False, counts_toward_source_readiness=False,
        media_selection='media_selection.json', demo_metrics=metrics,
        offline_assurance={k: v for k, v in demo_usability.items() if k != 'places'})
    demo_manifest['counts']['with_images'] = len(image_manifest)
    atomic_json(demo / 'manifest.json', demo_manifest)
    preview_rows = []
    for pid, record in records.items():
        place = by_id[pid]
        selection = selections.get(pid, {})
        image = selection.get('image')
        if not image:
            continue
        selected_class = selection['media_class']
        license_note = 'reusable license unverified' if selected_class == 'TEST_ONLY_REAL' else 'selected approved media'
        strict_status = 'RESOLVED' if selected_class == 'VERIFIED_REAL' else 'UNRESOLVED'
        preview_rows.append(f'<article data-place-id="{escape(pid)}"><h2>{escape(place["name"])}</h2>'
            f'<p>{escape(selected_class)} · local demo · {license_note}</p>'
            f'<section><h3>Offline card thumbnail</h3><img class="thumb" src="{escape(image["thumbnail_path"])}" alt="{escape(place["name"])} thumbnail"></section>'
            f'<section><h3>Offline place detail</h3><img src="{escape(image["local_path"])}" alt="{escape(place["name"])}"></section>'
            f'<p>Source: <a href="{escape(image["source_page"])}">{escape(image["source"])}</a></p>'
            f'<p>Strict verified media: {strict_status}. Test-only photographs do not contribute to production coverage.</p></article>')
    (demo / 'preview.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\' data:; style-src \'unsafe-inline\'">'
        '<title>YatraCanvas offline demo media</title><style>body{font:16px system-ui;margin:2rem auto;max-width:900px;padding:0 1rem;background:#f7fafc;color:#2d3748}'
        'article{padding:1.5rem;background:white;border:1px solid #e2e8f0;border-radius:12px}img{max-width:100%;height:auto}.thumb{max-width:300px}section{margin:1.5rem 0}a{color:#2b6cb0}</style>'
        '<h1>YatraCanvas local demo</h1>' + ''.join(preview_rows) + '</html>', encoding='utf-8')
    checksums = {p.relative_to(demo).as_posix(): compute_sha256(p)
        for p in demo.rglob('*') if p.is_file() and p.name not in {'checksums.json', 'manifest.json'}}
    atomic_json(demo / 'checksums.json', checksums)
    demo_manifest['checksums'] = checksums
    atomic_json(demo / 'manifest.json', demo_manifest)
    from .validate import validate_release_package
    validate_release_package(demo)
    return metrics


def publish_test_media(source, file, confirmation_file, *, output_version, allow_test_media=False, settings=None):
    if not allow_test_media:
        raise ValueError('EXPLICIT_ALLOW_TEST_MEDIA_REQUIRED')
    settings = settings or get_settings()
    lock = settings.data_dir / 'test_media/.import-lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError('Another test media import is active') from None
    try:
        return _publish_test_media(source, file, confirmation_file, output_version=output_version,
            allow_test_media=allow_test_media, settings=settings)
    finally:
        lock.rmdir()


def _publish_test_media(source, file, confirmation_file, *, output_version, allow_test_media=False, settings=None):
    """Publish a new demo-capable pack. The strict research head is not changed."""
    settings = settings or get_settings()
    if not allow_test_media:
        raise ValueError('EXPLICIT_ALLOW_TEST_MEDIA_REQUIRED')
    if not output_version or Path(output_version).name != output_version or any(c in output_version for c in '/\\') or output_version in {'.', '..', 'v3'}:
        raise ValueError('NEW_SINGLE_DIRECTORY_VERSION_REQUIRED')
    source, file, confirmation_file = Path(source).resolve(), Path(file), Path(confirmation_file)
    if not source.is_relative_to(settings.releases_dir.resolve()):
        raise ValueError('INVALID_SOURCE_PACK')
    from ..research.export import snapshot, city_key, read_assurance
    from .validate import validate_release_package
    validate_release_package(source)
    signature = snapshot(source)
    city = json.loads((source / 'city.json').read_text(encoding='utf-8'))
    head_file = settings.data_dir / 'research/heads' / (city_key(city) + '.json')
    head = json.loads(head_file.read_text(encoding='utf-8')) if head_file.exists() else None
    if head and (head['snapshot'] != signature or (settings.releases_dir / head['output_pack']).resolve() != source):
        raise ValueError('STALE_STRICT_SOURCE_HEAD')
    places = json.loads((source / 'places.json').read_text(encoding='utf-8'))
    confirmation = ManualTestMediaConfirmation.model_validate_json(confirmation_file.read_text(encoding='utf-8'))
    place = next((p for p in places if p['id'] == confirmation.place_id), None)
    if place is None:
        raise ValueError('UNKNOWN_PLACE_ID')
    from .repair import human_field_locks
    locks = human_field_locks(settings, city)
    if {'images', 'images.primary', 'media'} & locks.get(place['id'], set()):
        raise ValueError('HUMAN_MEDIA_LOCK')
    work = settings.staging_dir / 'test_media' / uuid.uuid4().hex
    work.mkdir(parents=True)
    record = normalize_test_media(place, file, confirmation.model_dump(mode='json'), work)
    registry_file = settings.data_dir / 'test_media' / city_key(city) / 'registry.json'
    records = {}
    if registry_file.is_file():
        registry = json.loads(registry_file.read_text(encoding='utf-8'))
        previous = Path(registry['output_pack']).resolve()
        if not previous.is_relative_to(settings.releases_dir.resolve()):
            raise ValueError('INVALID_TEST_MEDIA_REGISTRY_PATH')
        by_id = {p['id']: p for p in places}
        for pid, previous_record in registry['records'].items():
            if pid == place['id']:
                continue
            if pid not in by_id or not valid_test_record(by_id[pid], previous_record, previous):
                raise ValueError('STALE_OR_INVALID_PREVIOUS_TEST_MEDIA')
            for key in ('local_path', 'thumbnail_path'):
                relative = previous_record['image'][key]
                target = (work / relative).resolve()
                if not target.is_relative_to(work.resolve()):
                    raise ValueError('INVALID_TEST_MEDIA_PATH')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(previous / relative, target)
            records[pid] = previous_record
    records[place['id']] = record
    if snapshot(source) != signature or (head_file.exists() and json.loads(head_file.read_text(encoding='utf-8')) != head):
        raise ValueError('STALE_STRICT_SOURCE_HEAD')
    from .offline_export import export_offline
    report = {'assurance': read_assurance(source),
        'field_provenance': json.loads((source / 'field_provenance.json').read_text(encoding='utf-8')),
        'ai_usage': {'paid_calls': 0, 'provider_calls': 0}, 'fallback_strategy': 'app',
        'test_media_records': records,
        'test_media_import': {'confirmation_sha256': compute_sha256(confirmation_file),
            'source_snapshot': signature, 'source_pack': str(source), 'strict_head_unchanged': True}}
    old_report = source / 'ai_repair.json'
    if old_report.is_file():
        prior = json.loads(old_report.read_text(encoding='utf-8'))
        if prior.get('manual_resolution'):
            report['manual_resolution'] = prior['manual_resolution']
    output, strict = export_offline(source, source.parent / output_version, places, work, report)
    atomic_json(registry_file, {'schema_version': '1.0', 'output_pack': str(output),
        'source_snapshot': signature, 'records': records, 'usage_scope': 'local_testing_only'})
    return {'output_pack': str(output), 'record': record,
        'strict_metrics': {k: strict[k] for k in ('real_required_total', 'real_required_verified', 'REAL_REQUIRED_MEDIA_COVERAGE', 'SOURCE_DATA_READY')},
        'demo_metrics': report['demo_media_metrics'], 'paid_calls': 0, 'provider_calls': 0,
        'strict_head_unchanged': True}
