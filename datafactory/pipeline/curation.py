"""Apply CityPack Lab human curation with deterministic, fail-closed semantics."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple


class CurationApplicationError(RuntimeError):
    """Raised when human work cannot be reconciled with refreshed provider data."""

    def __init__(
        self, message: str, *, report: "CurationReconciliation | None" = None
    ) -> None:
        self.report = report
        super().__init__(message)


@dataclass
class CurationReconciliation:
    applied_additions: List[str] = field(default_factory=list)
    applied_overrides: List[str] = field(default_factory=list)
    applied_exclusions: List[str] = field(default_factory=list)
    applied_media: List[str] = field(default_factory=list)
    orphaned_overrides: List[str] = field(default_factory=list)
    orphaned_exclusions: List[str] = field(default_factory=list)
    orphaned_media: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["needs_human_review"] = bool(self.blockers)
        return value

    @property
    def blockers(self) -> List[str]:
        result = list(self.conflicts)
        for label, values in (
            ("orphaned overrides", self.orphaned_overrides),
            ("orphaned exclusions", self.orphaned_exclusions),
            ("orphaned media", self.orphaned_media),
        ):
            if values:
                result.append(f"{label}: {', '.join(sorted(values))}")
        return result


def _records(directory: Path) -> List[Tuple[Path, Dict[str, Any]]]:
    result: List[Tuple[Path, Dict[str, Any]]] = []
    if not directory.is_dir():
        return result
    for path in sorted(directory.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CurationApplicationError(f"invalid curation file {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise CurationApplicationError(f"invalid curation file {path}: expected object")
        result.append((path, value))
    return result


def _identifier(data: Dict[str, Any], path: Path) -> str:
    value = data.get("place_id") or data.get("placeId") or data.get("id")
    if not isinstance(value, str) or not value.strip():
        raise CurationApplicationError(f"missing place id in {path}")
    return value.strip()


def _portable_path(root: Path, raw: Any, source: Path) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise CurationApplicationError(f"empty media path in {source}")
    candidate = (root / Path(*raw.replace("\\", "/").split("/"))).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise CurationApplicationError(f"media path escapes curation root in {source}") from exc
    return candidate


def _apply_override(place: Dict[str, Any], data: Dict[str, Any]) -> None:
    fields = (
        "name",
        "name_hi",
        "category",
        "subcategory",
        "latitude",
        "longitude",
        "address",
        "opening_hours",
        "website",
        "phone",
        "description",
        "tier",
    )
    for name in fields:
        if name in data and data[name] is not None:
            place[name] = data[name]
    if data.get("is_core") is True and "tier" not in data:
        place["tier"] = "core_destination"


def _addition(data: Dict[str, Any], path: Path, city_id: str) -> Dict[str, Any]:
    place_id = _identifier(data, path)
    required = ("name", "category", "author", "evidence_source")
    missing = [name for name in required if not str(data.get(name) or "").strip()]
    try:
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CurationApplicationError(f"invalid coordinates in {path}") from exc
    if missing or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        detail = ", ".join(missing) if missing else "coordinates"
        raise CurationApplicationError(f"invalid manual addition {path}: {detail}")
    record_city = data.get("city_id") or data.get("cityId") or city_id
    if record_city != city_id:
        raise CurationApplicationError(
            f"manual addition {path} belongs to {record_city}, expected {city_id}"
        )
    return {
        "canonical_id": place_id,
        "name": data["name"],
        "name_en": data.get("name_en") or data["name"],
        "name_hi": data.get("name_hi"),
        "alternate_names": data.get("alternate_names", []),
        "alternate_name_records": [],
        "latitude": latitude,
        "longitude": longitude,
        "address": data.get("address"),
        "category": data["category"],
        "subcategory": data.get("subcategory"),
        "tier": data.get("tier") or "recommended",
        "website": data.get("website"),
        "phone": data.get("phone"),
        "opening_hours": data.get("opening_hours"),
        "opening_hours_source": "manual_curation" if data.get("opening_hours") else None,
        "description": data.get("description"),
        "tags": data.get("tags", []),
        "sources_provenance": [
            {
                "source": "manual_curation",
                "source_id": data["evidence_source"],
                "retrieved_at": data.get("created_at"),
            }
        ],
        "field_provenance": [],
        "image_metadata": None,
        "gallery_metadata": [],
    }


def _apply_media(
    place: Dict[str, Any],
    data: Dict[str, Any],
    path: Path,
    curation_dir: Path,
    media_dir: Path,
) -> Dict[str, Any]:
    required = (
        "primaryImagePath",
        "thumbnailImagePath",
        "originalFilename",
        "source",
        "sourcePage",
        "author",
        "license",
        "licenseUrl",
        "contributor",
        "importedAt",
    )
    missing = [name for name in required if not str(data.get(name) or "").strip()]
    for name in (
        "originalWidth",
        "originalHeight",
        "primaryWidth",
        "primaryHeight",
    ):
        if not isinstance(data.get(name), int) or data[name] <= 0:
            missing.append(name)
    sha = str(data.get("originalSha256") or "")
    if len(sha) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in sha):
        missing.append("originalSha256")
    if missing:
        raise CurationApplicationError(
            f"incomplete curated media {path}: {', '.join(sorted(set(missing)))}"
        )
    place_id = place["canonical_id"]
    primary_source = _portable_path(curation_dir, data["primaryImagePath"], path)
    thumbnail_source = _portable_path(curation_dir, data["thumbnailImagePath"], path)
    if not primary_source.is_file() or not thumbnail_source.is_file():
        raise CurationApplicationError(f"curated media bytes are missing for {place_id}")
    destination = media_dir / place_id
    destination.mkdir(parents=True, exist_ok=True)
    primary_target = destination / "primary.webp"
    thumbnail_target = destination / "thumbnail.webp"
    shutil.copy2(primary_source, primary_target)
    shutil.copy2(thumbnail_source, thumbnail_target)
    metadata = {
        "source": data["source"],
        "source_page": data["sourcePage"],
        "original_file": data["originalFilename"],
        "author": data["author"],
        "license": data["license"],
        "license_url": data["licenseUrl"],
        "attribution": f"{data['author']} via {data['source']}",
        "width": int(data.get("primaryWidth") or 0),
        "height": int(data.get("primaryHeight") or 0),
        "match_method": "verified_human_curation",
        "match_confidence": 1.0,
        "downloaded_at": data["importedAt"],
        "local_path": f"images/{place_id}/primary.webp",
        "thumbnail_path": f"images/{place_id}/thumbnail.webp",
    }
    place["image_metadata"] = metadata
    place["gallery_metadata"] = []
    return {"primary": metadata, "gallery": []}


def apply_human_curation(
    places: List[Dict[str, Any]],
    *,
    city_id: str,
    curation_dir: Path,
    media_dir: Path,
    images_manifest: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], CurationReconciliation]:
    """Merge provider output with durable human work; human values win on exact IDs."""

    report = CurationReconciliation()
    by_id = {str(place["canonical_id"]): dict(place) for place in places}
    for path, data in _records(curation_dir / "additions"):
        place_id = _identifier(data, path)
        if place_id in by_id:
            report.conflicts.append(f"addition conflicts with provider id {place_id}")
            continue
        try:
            by_id[place_id] = _addition(data, path, city_id)
            report.applied_additions.append(place_id)
        except CurationApplicationError as exc:
            report.conflicts.append(str(exc))
    for path, data in _records(curation_dir / "overrides"):
        place_id = _identifier(data, path)
        if data.get("verified") is not True:
            report.conflicts.append(f"unverified override {path}")
        elif place_id not in by_id:
            report.orphaned_overrides.append(place_id)
        else:
            _apply_override(by_id[place_id], data)
            report.applied_overrides.append(place_id)
    for path, data in _records(curation_dir / "exclusions"):
        place_id = _identifier(data, path)
        if not str(data.get("reason") or "").strip():
            report.conflicts.append(f"exclusion has no reason {path}")
        elif place_id not in by_id:
            report.orphaned_exclusions.append(place_id)
        else:
            del by_id[place_id]
            images_manifest.pop(place_id, None)
            report.applied_exclusions.append(place_id)
    for path, data in _records(curation_dir / "media"):
        place_id = _identifier(data, path)
        if place_id not in by_id:
            report.orphaned_media.append(place_id)
            continue
        try:
            images_manifest[place_id] = _apply_media(
                by_id[place_id], data, path, curation_dir, media_dir
            )
            report.applied_media.append(place_id)
        except CurationApplicationError as exc:
            report.conflicts.append(str(exc))
    if report.blockers:
        raise CurationApplicationError("; ".join(report.blockers), report=report)
    return list(by_id.values()), images_manifest, report


def reapply_human_overrides(
    places: List[Dict[str, Any]], *, curation_dir: Path
) -> List[Dict[str, Any]]:
    """Restore authoritative human fields after generated scoring defaults run."""

    by_id = {str(place["canonical_id"]): dict(place) for place in places}
    for path, data in _records(curation_dir / "overrides"):
        place_id = _identifier(data, path)
        if place_id not in by_id or data.get("verified") is not True:
            raise CurationApplicationError(f"cannot reapply override {path}")
        _apply_override(by_id[place_id], data)
    return list(by_id.values())


def write_reconciliation(
    path: Path, report: CurationReconciliation, *, curation_dir: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    payload["curation_revision"] = _curation_revision(curation_dir)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _curation_revision(curation_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(curation_dir.rglob("*.json")) if curation_dir.is_dir() else []:
        digest.update(path.relative_to(curation_dir).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()
