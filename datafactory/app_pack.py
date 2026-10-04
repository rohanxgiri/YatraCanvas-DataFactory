"""Small, indexed Flutter projection of an immutable canonical release."""
import json
import re
import shutil
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .config.settings import get_settings
from .exporters.sqlite_exporter import export_sqlite
from .models.city import CityMetadata
from .models.place import Place
from .pipeline.test_media import select_display_media
from .pipeline.validate import validate_release_package
from .research.export import find_pack, snapshot, read_assurance
from .utils.atomic import atomic_json
from .utils.hashing import compute_sha256

SCHEMA_VERSION = 1


def safe_file(root, relative):
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ValueError('Invalid relative pack path')
    path = (Path(root) / relative).resolve()
    if not path.is_relative_to(Path(root).resolve()) or Path(relative).is_absolute():
        raise ValueError('Pack path escapes root')
    return path


def validate_app_pack(root):
    root = Path(root)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['schema_version'] != SCHEMA_VERSION or manifest.get('validated') is not True:
        raise ValueError('Unsupported or unvalidated runtime pack')
    expected = manifest['checksums']
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.relative_to(root).as_posix() != 'manifest.json'}
    if actual != set(expected):
        raise ValueError('Runtime pack file inventory mismatch')
    for relative, checksum in expected.items():
        if compute_sha256(safe_file(root, relative)) != checksum:
            raise ValueError(f'Runtime pack checksum mismatch: {relative}')
        if relative.startswith('media/'):
            from PIL import Image
            with Image.open(safe_file(root, relative)) as image:
                image.verify()
    with closing(sqlite3.connect((root / 'city_pack.sqlite').resolve().as_uri() + '?mode=ro', uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Runtime database integrity failed')
        if db.execute('SELECT count(*) FROM places').fetchone()[0] != manifest['place_count']:
            raise ValueError('Runtime place count mismatch')
        if db.execute('SELECT id FROM cities').fetchone()[0] != manifest['city_id']:
            raise ValueError('Runtime city mismatch')
        for primary, thumb in db.execute('SELECT primary_image_path, thumbnail_image_path FROM places'):
            for relative in (primary, thumb):
                if relative and relative not in expected:
                    raise ValueError('Missing referenced runtime image')
    return manifest


def export_app_pack(city, *, version=None, output=None, dry_run=False, allow_test_media=False,
                    state=None, country=None, settings=None):
    settings = settings or get_settings()
    source = find_pack(city, state=state, country=country, version=version, settings=settings)
    validate_release_package(source)
    signature = snapshot(source)
    metadata = CityMetadata.model_validate_json((source / 'city.json').read_text(encoding='utf-8'))
    raw = json.loads((source / 'places.json').read_text(encoding='utf-8'))
    output = Path(output) if output else settings.releases_dir / 'app_packs' / metadata.id / (source.name + ('-test-media' if allow_test_media else ''))
    if output.resolve().is_relative_to(source.resolve()) or source.resolve().is_relative_to(output.resolve()):
        raise ValueError('Runtime output must be separate from canonical source')
    summary = {'city_id': metadata.id, 'source_release': source.name, 'source_snapshot': signature,
               'output': str(output), 'place_count': len(raw), 'dry_run': dry_run}
    if dry_run:
        return summary
    if output.exists():
        existing = validate_app_pack(output)
        if existing['source_snapshot'] == signature and existing['allow_test_media'] == allow_test_media:
            return {**summary, **existing, 'reused': True, 'output': str(output)}
        raise ValueError('Runtime outputs are immutable, choose another output')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.parent / ('.app-pack-' + uuid.uuid4().hex)
    staging.mkdir()
    try:
        assurance = read_assurance(source)
        tests_file = source / 'test_media_manifest.json'
        test_records = json.loads(tests_file.read_text(encoding='utf-8')).get('records', {}) if tests_file.exists() else {}
        selections = {}
        projected = []
        for row in raw:
            selection = select_display_media(row, assurance, test_records, source, allow_test_media=allow_test_media)
            image = selection['image'] if selection else None
            # The application already has its own fallback library.
            if selection and selection['media_class'] not in {'VERIFIED_REAL', 'TEST_ONLY_REAL'}:
                image = None
            if image:
                image = dict(image)
                for key, filename in [('local_path', 'primary.webp'), ('thumbnail_path', 'thumbnail.webp')]:
                    original = safe_file(source, image[key])
                    relative = f'media/{row["id"]}/{filename}'
                    target = safe_file(staging, relative)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    # Existing pipeline already normalized orientation and WebP size.
                    shutil.copyfile(original, target)
                    image[key] = relative
                selections[row['id']] = {**selection, 'image': image}
            item = dict(row)
            item['images'] = {'primary': image, 'gallery': []}
            projected.append(Place.model_validate(item))
        database = staging / 'city_pack.sqlite'
        export_sqlite(metadata, projected, database)
        with sqlite3.connect(database) as db:
            for column in ['name_en TEXT', 'aliases TEXT', 'normalized_name TEXT', 'opening_hours_normalized TEXT',
                           'opening_hours_status TEXT', 'media_class TEXT', 'image_metadata TEXT', 'runtime_category TEXT']:
                db.execute('ALTER TABLE places ADD COLUMN ' + column)
            db.execute('CREATE VIRTUAL TABLE place_search USING fts5(place_id UNINDEXED, name, name_en, aliases, searchable_text, tokenize="unicode61 remove_diacritics 2")')
            for row in raw:
                hours = row['opening_hours']
                status = ('VERIFIED' if hours.get('verified') else 'UNVERIFIED') if hours.get('normalized') or hours.get('raw') else 'UNKNOWN'
                selection = selections.get(row['id'])
                image = selection['image'] if selection else None
                category = runtime_category(row['classification']['category'], row['classification'].get('subcategory'))
                db.execute('UPDATE places SET name_en=?, aliases=?, normalized_name=?, opening_hours_normalized=?, opening_hours_status=?, media_class=?, image_metadata=?, runtime_category=? WHERE id=?',
                           (row.get('name_en'), json.dumps(row.get('alternate_names', [])), row['name'].casefold(),
                            hours.get('normalized'), status, selection['media_class'] if selection else None,
                            json.dumps(image) if image else None, category, row['id']))
                db.execute('INSERT INTO place_search VALUES (?,?,?,?,?)', (row['id'], row['name'], row.get('name_en'),
                           ' '.join(row.get('alternate_names', [])), ' '.join(filter(None, [row.get('description'), row['classification']['category']]))))
            db.execute('CREATE INDEX idx_runtime_category ON places(runtime_category, travel_relevance_score DESC)')
            db.execute('CREATE INDEX idx_runtime_name ON places(normalized_name)')
            db.execute('CREATE INDEX idx_runtime_hours ON places(opening_hours_status)')
            db.execute('CREATE INDEX idx_runtime_media ON places(media_class)')
            db.execute('ANALYZE')
        db.close()
        checksums = {p.relative_to(staging).as_posix(): compute_sha256(p) for p in staging.rglob('*') if p.is_file()}
        manifest = {**summary, 'pack_version': source.name, 'schema_version': SCHEMA_VERSION,
                    'name': metadata.name, 'state': metadata.state, 'country': metadata.country,
                    'latitude': metadata.center[0], 'longitude': metadata.center[1], 'timezone': metadata.timezone,
                    'generated_at': datetime.now(timezone.utc).isoformat(), 'validated': True,
                    'allow_test_media': allow_test_media, 'production_release': False,
                    'strict_source_ready': json.loads((source / 'manifest.json').read_text(encoding='utf-8')).get('offline_assurance', {}).get('SOURCE_DATA_READY', False),
                    'database_sha256': checksums['city_pack.sqlite'], 'checksums': checksums,
                    'media_count': len(selections), 'opening_hours_count': sum(bool(p.opening_hours.raw) for p in projected),
                    'verified_hours_count': sum(p.opening_hours.verified for p in projected),
                    'database_bytes': database.stat().st_size,
                    'media_bytes': sum(p.stat().st_size for p in (staging / 'media').rglob('*') if p.is_file()) if (staging / 'media').exists() else 0}
        manifest.pop('output'); manifest.pop('dry_run')
        atomic_json(staging / 'manifest.json', manifest)
        validate_app_pack(staging)
        if snapshot(source) != signature:
            raise ValueError('Source changed during export')
        staging.rename(output)
        return {**manifest, 'output': str(output)}
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def runtime_category(category, subcategory=None):
    text = f'{category} {subcategory or ""}'.lower()
    for result, terms in [('cafe', ['cafe', 'coffee']), ('food', ['restaurant', 'food', 'dining']),
                          ('religious', ['religio', 'temple', 'mosque', 'church', 'worship']),
                          ('markets', ['market', 'shopping', 'bazaar']), ('nature', ['nature', 'park', 'garden', 'natural']),
                          ('heritage', ['heritage', 'historic', 'fort', 'palace', 'monument'])]:
        if any(term in text for term in terms):
            return result
    return 'tourism'
