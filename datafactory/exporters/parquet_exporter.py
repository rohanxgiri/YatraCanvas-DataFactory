import json
from pathlib import Path
from typing import List
import pyarrow as pa
import pyarrow.parquet as pq
from ..models.place import Place


def export_places_parquet(places: List[Place], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for p in places:
        rows.append({
            "id": p.id,
            "name": p.name,
            "alternate_names": json.dumps(p.alternate_names, ensure_ascii=False),
            "city_id": p.city.id,
            "city_name": p.city.name,
            "state": p.city.state,
            "country": p.city.country,
            "latitude": p.location.latitude,
            "longitude": p.location.longitude,
            "address": p.location.address,
            "category": p.classification.category,
            "subcategory": p.classification.subcategory,
            "tags": json.dumps(p.classification.tags, ensure_ascii=False),
            "recommended_visit_minutes": p.planning.recommended_visit_minutes,
            "tourism_priority": p.planning.tourism_priority,
            "website": p.contact.website,
            "phone": p.contact.phone,
            "opening_hours": p.opening_hours.raw,
            "primary_image_path": p.images.primary.local_path if p.images.primary else None,
            "primary_image_license": p.images.primary.license if p.images.primary else None,
            "primary_image_author": p.images.primary.author if p.images.primary else None,
            "overture_id": p.external_ids.overture_id,
            "osm_id": p.external_ids.osm_id,
            "wikidata_id": p.external_ids.wikidata_id,
            "quality_overall": p.quality.overall,
            "generated_at": p.generated_at,
            "schema_version": p.schema_version,
        })

    table = pa.Table.from_pylist(rows)
    pq.write_table(table, output_path)
