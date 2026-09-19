import json
from pathlib import Path
from typing import Dict, Any, List
from ..models.city import CityMetadata
from ..models.place import Place


def export_places_json(places: List[Place], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([p.model_dump() for p in places], f, ensure_ascii=False, indent=2)


def export_places_jsonl(places: List[Place], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for p in places:
            f.write(json.dumps(p.model_dump(), ensure_ascii=False) + "\n")


def export_city_json(city_meta: CityMetadata, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(city_meta.model_dump(), f, ensure_ascii=False, indent=2)


def export_images_manifest(manifest: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def export_sources_json(sources: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
