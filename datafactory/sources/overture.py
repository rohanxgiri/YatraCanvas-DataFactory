import datetime
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
import overturemaps
import pyarrow.parquet as pq
import pyarrow as pa
from shapely import wkb

from ..config.settings import get_settings
from ..utils.geo import expand_bbox


class OverturePlacesSource:
    def __init__(self):
        self.settings = get_settings()

    def fetch_places(
        self,
        bbox: Tuple[float, float, float, float],
        output_raw_path: Path
    ) -> List[Dict[str, Any]]:
        """
        Fetch Overture Places for the given bbox (min_lon, min_lat, max_lon, max_lat).
        Saves raw immutable data to output_raw_path.
        """
        if output_raw_path.exists():
            # Return cached raw data
            print(f"Loading raw Overture places from cache: {output_raw_path}")
            table = pq.read_table(output_raw_path)
            return self._parse_table(table)

        output_raw_path.parent.mkdir(parents=True, exist_ok=True)
        min_lon, min_lat, max_lon, max_lat = bbox

        print(f"Querying Overture Maps Places for bbox: {bbox}...")
        reader = overturemaps.record_batch_reader(
            "place",
            bbox=(min_lon, min_lat, max_lon, max_lat),
        )

        batches = []
        while True:
            try:
                batch = reader.read_next_batch()
                batches.append(batch)
            except StopIteration:
                break
            except Exception as e:
                print(f"Overture batch read finished or interrupted: {e}")
                break

        if not batches:
            print("No Overture places found in the specified bounding box.")
            return []

        table = pa.Table.from_batches(batches)
        # Write immutable raw parquet
        pq.write_table(table, output_raw_path)
        print(f"Saved {len(table)} raw Overture places to {output_raw_path}")

        return self._parse_table(table)

    def _parse_table(self, table: pa.Table) -> List[Dict[str, Any]]:
        records = []
        pydict = table.to_pydict()
        num_rows = len(table)

        col_ids = pydict.get("id", [])
        col_names = pydict.get("names", [])
        col_geoms = pydict.get("geometry", [])
        col_basic_cat = pydict.get("basic_category", [])
        col_taxonomy = pydict.get("taxonomy", [])
        col_cats = pydict.get("categories", [])
        col_websites = pydict.get("websites", [])
        col_phones = pydict.get("phones", [])
        col_addresses = pydict.get("addresses", [])
        col_confidence = pydict.get("confidence", [])
        col_operating_status = pydict.get("operating_status", [])
        col_brand = pydict.get("brand", [])
        col_sources = pydict.get("sources", [])

        for i in range(num_rows):
            # Parse geometry
            geom_bytes = col_geoms[i] if i < len(col_geoms) else None
            lat, lon = None, None
            if geom_bytes:
                try:
                    pt = wkb.loads(geom_bytes)
                    lat, lon = round(pt.y, 6), round(pt.x, 6)
                except Exception:
                    pass

            # Parse names
            name_obj = col_names[i] if i < len(col_names) else {}
            primary_name = None
            alternate_names = []
            if isinstance(name_obj, dict):
                primary_name = name_obj.get("primary")
                common_rules = name_obj.get("common", {})
                if isinstance(common_rules, dict):
                    for v in common_rules.values():
                        if v and v != primary_name and v not in alternate_names:
                            alternate_names.append(v)
                rules = name_obj.get("rules", [])
                if isinstance(rules, list):
                    for r in rules:
                        if isinstance(r, dict) and r.get("value") and r.get("value") != primary_name:
                            alternate_names.append(r.get("value"))

            if not primary_name:
                continue

            # Parse categories
            basic_cat = col_basic_cat[i] if i < len(col_basic_cat) else None
            tax = col_taxonomy[i] if i < len(col_taxonomy) else None
            cats_obj = col_cats[i] if i < len(col_cats) else {}

            # Parse websites and phones
            websites = col_websites[i] if i < len(col_websites) else []
            website = websites[0] if isinstance(websites, list) and websites else None
            phones = col_phones[i] if i < len(col_phones) else []
            phone = phones[0] if isinstance(phones, list) and phones else None

            # Parse address
            address_str = None
            addrs = col_addresses[i] if i < len(col_addresses) else []
            if isinstance(addrs, list) and addrs and isinstance(addrs[0], dict):
                address_str = addrs[0].get("freeform")

            records.append({
                "source": "overture",
                "id": col_ids[i] if i < len(col_ids) else None,
                "name": primary_name,
                "alternate_names": alternate_names,
                "latitude": lat,
                "longitude": lon,
                "basic_category": basic_cat,
                "taxonomy": tax,
                "categories": cats_obj,
                "website": website,
                "phone": phone,
                "address": address_str,
                "confidence": col_confidence[i] if i < len(col_confidence) else None,
                "operating_status": col_operating_status[i] if i < len(col_operating_status) else None,
                "brand": col_brand[i] if i < len(col_brand) else None,
                "sources": col_sources[i] if i < len(col_sources) else [],
            })

        return records
