# Isolated fixture round trip

All schedules, photographs, metadata and router decisions in this fixture are synthetic. They do not claim real venue facts or licenses. No production release was changed.

```json
{
  "fixture_only": true,
  "fixture_root": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\scratch\\fixture-roundtrip-sfh0eevl",
  "export": {
    "city": {
      "id": "jaipur",
      "name": "Jaipur",
      "state": "Rajasthan",
      "country": "India"
    },
    "handoff_id": "handoff_2a6f0ff2bb48f294c752a747",
    "total": 3,
    "filtered_total_before_limit": 3,
    "remaining_in_filter": 0,
    "actionable": 3,
    "deferred_optional": 0,
    "do_not_research": 0,
    "by_type": {
      "OPENING_HOURS": 1,
      "REAL_PRIMARY_IMAGE": 1,
      "WEBSITE": 0,
      "DESCRIPTION": 1,
      "COORDINATE_RESEARCH": 0,
      "IDENTITY_RESEARCH": 0
    },
    "by_priority": {
      "P0": 1,
      "P1": 0,
      "P2": 2,
      "P3": 0,
      "P4": 0
    },
    "output": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\scratch\\fixture-roundtrip-sfh0eevl\\handoff",
    "zero_candidate_media_tasks": 1
  },
  "command_exit_codes": {
    "research-import --dry-run": 0,
    "research-import --apply": 0
  },
  "offline_rebuild": "Completed atomically by apply; validate_release_package passed for JSON/JSONL/Parquet/SQLite/media/checksums",
  "changed_place_fields": [
    "opening_hours",
    "images"
  ],
  "provenance_rows": 2,
  "original_v3_preserved": true,
  "readiness_before": {
    "GENERAL_USABILITY": 0.0,
    "REAL_REQUIRED_MEDIA_COVERAGE": 0.0,
    "SOURCE_DATA_READY": false,
    "critical_blockers": {
      "CORE_MEDIA_UNRESOLVED": 1,
      "MEDIA_NOT_RENDERABLE": 1
    }
  },
  "readiness_after": {
    "GENERAL_USABILITY": 100.0,
    "REAL_REQUIRED_MEDIA_COVERAGE": 100.0,
    "SOURCE_DATA_READY": true,
    "critical_blockers": {}
  },
  "live_cloud_calls": 0,
  "real_research_results_applied": 0
}
```
