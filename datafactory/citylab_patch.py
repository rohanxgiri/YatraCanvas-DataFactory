"""Reviewed field patches publish new snapshots, never update release files."""
import copy
import hashlib
import json
import math
import re
import shutil
import uuid
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .app_pack import safe_file
from .config.settings import get_settings
from .models.place import Place
from .research.export import find_pack, snapshot, read_assurance, city_key
from .utils.atomic import atomic_json
from .utils.hashing import compute_sha256, generate_canonical_place_id

FIELDS = {'name': 'name', 'name_hi': 'name_hi', 'aliases': 'alternate_names', 'description': 'description',
          'category': 'classification.category', 'subcategory': 'classification.subcategory',
          'latitude': 'location.latitude', 'longitude': 'location.longitude', 'address': 'location.address',
          'website': 'contact.website', 'phone': 'contact.phone', 'tier': 'tier',
          'opening_hours': 'opening_hours', 'media': 'images'}


def get_value(record, field):
    value = record
    for key in FIELDS[field].split('.'):
        value = value.get(key) if isinstance(value, dict) else None
    return value


def set_value(record, field, value):
    path = FIELDS[field].split('.')
    parent = record
    for key in path[:-1]:
        parent = parent.setdefault(key, {})
    parent[path[-1]] = value


def validate_value(field, value):
    if field not in FIELDS:
        raise ValueError(f'Unsupported field: {field}')
    if field in {'latitude', 'longitude'}:
        bound = 90 if field == 'latitude' else 180
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or abs(value) > bound:
            raise ValueError('Invalid coordinates')
    elif field == 'aliases':
        if not isinstance(value, list) or len(value) > 100 or any(not isinstance(s, str) or not s.strip() for s in value):
            raise ValueError('Invalid aliases')
    elif field == 'opening_hours':
        if not isinstance(value, dict) or set(value) - {'raw', 'normalized', 'source', 'verified', 'confidence', 'retrieved_at', 'conflicts'}:
            raise ValueError('Invalid hours object')
        if not isinstance(value.get('verified', False), bool):
            raise ValueError('Invalid hours verification')
        text = value.get('normalized') or value.get('raw')
        if text:
            from .local_intelligence.hours import validate_hours
            if not validate_hours(text)['valid']:
                raise ValueError('Invalid opening hours')
        elif value.get('verified'):
            raise ValueError('Unknown hours cannot be verified')
    elif field == 'media':
        if value is not None and not isinstance(value, dict):
            raise ValueError('Invalid media update')
    elif value is not None and (not isinstance(value, str) or len(value) > 10000):
        raise ValueError(f'Invalid {field}')
    if field in {'name', 'category', 'tier'} and (not isinstance(value, str) or not value.strip()):
        raise ValueError(f'{field} is required')
    if field == 'website' and value and not re.match(r'^https?://[^\s/]+', value):
        raise ValueError('Website must be HTTP(S)')


def unpack_patch(file, root):
    with zipfile.ZipFile(file) as archive:
        infos = archive.infolist()
        if len(infos) > 2000 or sum(i.file_size for i in infos) > 250_000_000:
            raise ValueError('Patch exceeds size limits')
        seen = set()
        for info in infos:
            if info.filename in seen or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Duplicate or symbolic patch entry')
            seen.add(info.filename)
            target = safe_file(root, info.filename)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open('wb') as out:
                    shutil.copyfileobj(source, out)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    changes = json.loads((root / 'changes.json').read_text(encoding='utf-8'))
    if manifest.get('patch_schema_version') != 1 or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', manifest.get('patch_id', '')):
        raise ValueError('Invalid patch identity/schema')
    if not isinstance(changes, list) or manifest['change_count'] != len(changes):
        raise ValueError('Invalid change inventory')
    checksums = manifest['checksums']
    files = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.relative_to(root).as_posix() != 'manifest.json'}
    if files != set(checksums):
        raise ValueError('Patch file inventory mismatch')
    for name, sha in checksums.items():
        if compute_sha256(safe_file(root, name)) != sha:
            raise ValueError('Patch checksum mismatch')
    if manifest['media_count'] != sum(n.startswith('media/') for n in files):
        raise ValueError('Patch media inventory mismatch')
    return manifest, changes


def duplicate(candidate, records):
    names = {candidate['name'].strip().casefold(), *[n.casefold() for n in candidate.get('alternate_names', [])]}
    for record in records:
        other = {record['name'].strip().casefold(), *[n.casefold() for n in record.get('alternate_names', [])]}
        same_identifier = any(v and record.get('external_ids', {}).get(k) == v for k, v in candidate.get('external_ids', {}).items())
        nearby = abs(candidate['location']['latitude'] - record['location']['latitude']) < .001 and abs(candidate['location']['longitude'] - record['location']['longitude']) < .001
        if same_identifier or nearby and names & other:
            return record['id']
    return None


def import_citylab_patch(file, *, apply=False, output_version=None, allow_test_media=False, settings=None):
    settings = settings or get_settings()
    work = settings.staging_dir / 'citylab' / uuid.uuid4().hex
    work.mkdir(parents=True)
    lock = settings.data_dir / 'citylab' / '.import-lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError('Another City Lab import is active') from None
    try:
        manifest, changes = unpack_patch(Path(file), work / 'patch')
        source = find_pack(manifest['city_name'], state=manifest['state'], country=manifest['country'], settings=settings)
        from .pipeline.validate import validate_release_package
        validate_release_package(source)
        city = json.loads((source / 'city.json').read_text(encoding='utf-8'))
        if manifest['city_id'] != city['id']:
            raise ValueError('Wrong patch city')
        base = find_pack(city['name'], state=city['state'], country=city['country'], version=manifest['source_pack_version'], settings=settings)
        if snapshot(base) != manifest['source_pack_fingerprint']:
            raise ValueError('Patch source fingerprint mismatch')
        signature = snapshot(source)
        source_places = json.loads((source / 'places.json').read_text(encoding='utf-8'))
        base_records = {p['id']: p for p in json.loads((base / 'places.json').read_text(encoding='utf-8'))}
        records = {p['id']: copy.deepcopy(p) for p in source_places}
        assurance = read_assurance(source)
        provenance = json.loads((source / 'field_provenance.json').read_text(encoding='utf-8')) if (source / 'field_provenance.json').exists() else []
        decisions, touched = [], set()
        media_updates = []
        now = datetime.now(timezone.utc).isoformat()
        for change in changes:
            decision = {'place_id': change.get('place_id'), 'action': 'APPLY', 'reasons': []}
            try:
                pid, operation, edits = change['place_id'], change['operation'], change['changes']
                if pid in touched or operation not in {'UPDATE', 'ADD', 'MEDIA_UPDATE'} or not isinstance(edits, dict) or not edits:
                    raise ValueError('Invalid or duplicate operation')
                touched.add(pid)
                for field, value in edits.items():
                    validate_value(field, value)
                if operation == 'ADD':
                    required = {'name', 'category', 'latitude', 'longitude'}
                    if not required <= set(edits):
                        raise ValueError('New place missing required inputs')
                    expected = generate_canonical_place_id(city['country'], city['state'], city['name'], edits['name'])
                    if pid != expected or pid in records:
                        raise ValueError('New place identity collision or invalid stable ID')
                    record = Place.model_validate({'id': pid, 'name': edits['name'], 'city': {k: city[k] for k in ('id', 'name', 'state', 'country')},
                        'location': {'latitude': edits['latitude'], 'longitude': edits['longitude']},
                        'classification': {'category': edits['category']}, 'planning': {}, 'contact': {}, 'opening_hours': {},
                        'images': {}, 'external_ids': {}, 'quality': {}, 'sources': [], 'generated_at': now}).model_dump(mode='json')
                    collision = duplicate(record, records.values())
                    if collision:
                        decision.update(action='REVIEW', reasons=[f'Potential duplicate: {collision}'])
                else:
                    if pid not in records or pid not in base_records:
                        raise ValueError('Unknown place ID')
                    record = records[pid]
                    if operation == 'MEDIA_UPDATE' and set(edits) != {'media'}:
                        raise ValueError('MEDIA_UPDATE only accepts media')
                    before = change.get('before', {})
                    for field in edits:
                        actual = get_value(base_records[pid], field)
                        if field not in before or before[field] != actual:
                            raise ValueError(f'Incorrect base field value: {field}')
                        if get_value(record, field) != actual:
                            decision.update(action='REVIEW', reasons=[f'Field changed since patch base: {field}'])
                if decision['action'] == 'APPLY':
                    for field, value in edits.items():
                        old = get_value(record, field)
                        if field == 'media':
                            media_updates.append((pid, value))
                        else:
                            set_value(record, field, value)
                        provenance.append({'place_id': pid, 'field': FIELDS[field], 'old_value': old, 'new_value': value,
                            'patch_id': manifest['patch_id'], 'source': 'citylab_manual', 'author': change.get('author'), 'timestamp': now})
                    records[pid] = Place.model_validate(record).model_dump(mode='json')
                    if operation == 'ADD':
                        collision = duplicate(records[pid], [r for key, r in records.items() if key != pid])
                        if collision:
                            decision.update(action='REVIEW', reasons=[f'Potential duplicate: {collision}'])
                    if {'name', 'latitude', 'longitude', 'category', 'aliases'} & edits.keys():
                        assurance.setdefault(pid, {})['media'] = {'verified': False, 'reason': 'Identity changed in City Lab, re-review media'}
                    if {'latitude', 'longitude'} & edits.keys():
                        from .pipeline.geographic_assurance import geography
                        geo = geography(record, city)
                        assurance.setdefault(pid, {})['geography'] = geo
                        if geo['status'] != 'VALID':
                            decision.update(action='REVIEW', reasons=['Coordinates need city-boundary review'])
                # Decode and validate even during dry run.
                if 'media' in edits and edits['media'] is not None:
                    media = edits['media']
                    if media.get('media_class') not in {'TEST_ONLY_REAL', 'VERIFIED_REAL'}:
                        raise ValueError('Unsupported media class')
                    image = safe_file(work / 'patch', media['file'])
                    if not media['file'].startswith('media/'):
                        raise ValueError('Media file must be in media/')
                    from PIL import Image
                    with Image.open(image) as decoded:
                        if decoded.format not in {'PNG', 'JPEG', 'WEBP'} or decoded.width * decoded.height > 40_000_000:
                            raise ValueError('Invalid media type/dimensions')
                        width, height = decoded.size
                        decoded.verify()
                    if media.get('identity_confirmed') is not True or media.get('real_photograph_confirmed') is not True:
                        raise ValueError('Manual identity and real-photo confirmation required')
                    if media['media_class'] == 'TEST_ONLY_REAL' and not allow_test_media:
                        decision.update(action='REVIEW', reasons=['Explicit --allow-test-media required'])
                    elif media['media_class'] == 'VERIFIED_REAL':
                        from .pipeline.media_assurance import deterministic_filter
                        from .models.media_candidate import MediaCandidate
                        proof = MediaCandidate(source=media.get('source', ''), source_url=media.get('source_page', ''),
                            media_url=media.get('source_page', ''), title=media.get('original_filename', image.name),
                            creator=media.get('author'), license=media.get('license', ''), license_url=media.get('license_url'),
                            attribution=media.get('attribution'), width=width, height=height, mime_type='image/webp',
                            source_confidence=1, match_method='manual_exact_identity', original_license_verified=True)
                        checks = deterministic_filter(proof, image.read_bytes())
                        if not checks['accepted']:
                            raise ValueError('Strict media validation failed: ' + ','.join(checks['reason_codes']))
            except (ValueError, KeyError, TypeError, OSError) as error:
                decision.update(action='REJECT', reasons=[str(error)])
            decisions.append(decision)
        result = {'patch_id': manifest['patch_id'], 'source_release': source.name, 'source_snapshot': signature,
                  'decisions': decisions, 'summary': dict(Counter(d['action'] for d in decisions)), 'dry_run': not apply}
        if not apply:
            return result
        if any(d['action'] != 'APPLY' for d in decisions) or not decisions:
            raise ValueError('Patch has REVIEW/REJECT decisions or no changes; dry-run and resolve first')
        if not output_version or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', output_version) or output_version in {'.', '..'}:
            raise ValueError('A new single-directory output version is required')
        output = source.parent / output_version
        if output.exists():
            raise ValueError('Old releases are immutable; choose a new version')
        tests_file = source / 'test_media_manifest.json'
        test_records = json.loads(tests_file.read_text(encoding='utf-8')).get('records', {}) if tests_file.exists() else {}
        # Retain test media only when its identity still matches.
        from .pipeline.test_media import valid_test_record
        test_records = {pid: row for pid, row in test_records.items() if pid in records and valid_test_record(records[pid], row, source)}
        for row in test_records.values():
            for key in ('local_path', 'thumbnail_path'):
                relative = row['image'][key]
                target = safe_file(work, relative); target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(safe_file(source, relative), target)
        for pid, media in media_updates:
            test_records.pop(pid, None)
            records[pid]['images'] = {'primary': None, 'gallery': []}
            assurance.setdefault(pid, {})['media'] = {'verified': False, 'reason': 'City Lab media update'}
            if media is None:
                continue
            record = normalize_media(records[pid], media, safe_file(work / 'patch', media['file']), work)
            if media['media_class'] == 'TEST_ONLY_REAL':
                test_records[pid] = record
            else:
                records[pid]['images']['primary'] = record['image']
                from .pipeline.test_media import identity_hash
                assurance[pid]['media'] = {'verified': True, 'identity_hash': identity_hash(records[pid]), 'reason': 'Human identity and reusable media evidence reviewed'}
        if snapshot(source) != signature or find_pack(city['name'], state=city['state'], country=city['country'], settings=settings) != source:
            raise ValueError('Canonical head changed during patch review')
        from .pipeline.offline_export import export_offline
        report = {'assurance': assurance, 'field_provenance': provenance, 'ai_usage': {'paid_calls': 0, 'provider_calls': 0},
                  'fallback_strategy': 'app', 'test_media_records': test_records, 'citylab_import': result}
        output, _ = export_offline(source, output, list(records.values()), work, report)
        # Audit is already included in ai_repair.json and field_provenance.json.
        from .research.importer import _write_head
        _write_head(settings, city, output)
        result.update(output_pack=str(output), dry_run=False)
        atomic_json(settings.data_dir / 'citylab' / (manifest['patch_id'] + '.json'), result)
        return result
    finally:
        lock.rmdir()
        shutil.rmtree(work)


def normalize_media(place, media, file, root):
    from PIL import Image, ImageOps
    from .pipeline.test_media import identity_hash
    now = datetime.now(timezone.utc).isoformat()
    sha = compute_sha256(file)
    relative = f'media/citylab/{place["id"]}/{sha[:16]}'
    target = safe_file(root, relative); target.mkdir(parents=True)
    with Image.open(file) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        image.thumbnail((1280, 1280)); thumb = image.copy(); thumb.thumbnail((400, 400))
        image.save(target / 'primary.webp', 'WEBP', quality=88)
        thumb.save(target / 'thumbnail.webp', 'WEBP', quality=85)
    test = media['media_class'] == 'TEST_ONLY_REAL'
    metadata = {'image_type': 'test_only_real' if test else 'real', 'source': media.get('source') or 'City Lab manual upload',
        'source_page': media.get('source_page') or '', 'original_file': media.get('original_filename') or file.name,
        'author': media.get('author'), 'license': 'UNVERIFIED_TEST_ONLY' if test else media['license'],
        'license_url': None if test else media.get('license_url'), 'attribution': media.get('attribution') or 'Manually supplied, local testing only, license unverified',
        'width': image.width, 'height': image.height, 'match_method': 'manual_exact_identity_test_only' if test else 'manual_exact_identity',
        'match_confidence': 0.0 if test else 1.0, 'downloaded_at': now,
        'local_path': relative + '/primary.webp', 'thumbnail_path': relative + '/thumbnail.webp',
        'content_sha256': compute_sha256(target / 'primary.webp')}
    return {'schema_version': '1.0', 'place_id': place['id'], 'media_class': media['media_class'],
        'usage_scope': 'local_testing_only', 'license_verified': not test, 'identity_verified': True,
        'counts_toward_source_readiness': False, 'identity_hash': identity_hash(place), 'input_sha256': sha,
        'source_name': metadata['source'], 'source_page': metadata['source_page'], 'reference_image_url': media.get('source_page') or '',
        'original_filename': metadata['original_file'], 'imported_at': now, 'confirmed_by': media.get('contributor') or 'City Lab contributor',
        'identity_evidence': [{'source': 'manual_confirmation', 'supports': 'User confirmed exact place and real photograph'}], 'excluded_entities': [],
        'primary_sha256': compute_sha256(target / 'primary.webp'), 'thumbnail_sha256': compute_sha256(target / 'thumbnail.webp'), 'image': metadata}
