# Research prioritization after optimization

Counts below classify exactly the preserved 1,637 baseline tasks. The internal full inventory also records ordinary optional gaps omitted by the old selector. Default exports exclude P3, P4 and DO_NOT_RESEARCH.

| City | Before | P0 | P1 | P2 | P3 | P4 | No research | Default | Reduction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Jaipur | 771 | 53 | 1 | 56 | 281 | 269 | 111 | 110 | 85.73% |
| Udaipur | 264 | 55 | 1 | 53 | 61 | 58 | 36 | 109 | 58.71% |
| Varanasi | 471 | 112 | 0 | 92 | 49 | 118 | 100 | 204 | 56.69% |
| Manali | 131 | 14 | 7 | 15 | 39 | 42 | 14 | 36 | 72.52% |

| City | Required | Recommended | Optional defer | Do not research |
|---|---:|---:|---:|---:|
| Jaipur | 54 | 337 | 269 | 111 |
| Udaipur | 56 | 114 | 58 | 36 |
| Varanasi | 112 | 141 | 118 | 100 |
| Manali | 21 | 54 | 42 | 14 |

## Jaipur Batch 1

```json
{
  "city": {
    "id": "jaipur",
    "name": "Jaipur",
    "state": "Rajasthan",
    "country": "India"
  },
  "handoff_id": "handoff_94e20cc348cdae4f4b52c644",
  "total": 75,
  "filtered_total_before_limit": 110,
  "remaining_in_filter": 35,
  "actionable": 110,
  "deferred_optional": 924,
  "do_not_research": 1098,
  "by_type": {
    "OPENING_HOURS": 15,
    "REAL_PRIMARY_IMAGE": 50,
    "WEBSITE": 5,
    "DESCRIPTION": 1,
    "COORDINATE_RESEARCH": 4,
    "IDENTITY_RESEARCH": 0
  },
  "by_priority": {
    "P0": 53,
    "P1": 1,
    "P2": 21,
    "P3": 0,
    "P4": 0
  },
  "output": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\exports\\jaipur\\batch_1",
  "zero_candidate_media_tasks": 23
}
```

## Snapshot preservation and readiness

- Jaipur: source unchanged=True; v3 unchanged=True; general usability=1.17%; required media=3.85%; source ready=False
- Udaipur: source unchanged=True; v3 unchanged=True; general usability=0.93%; required media=1.82%; source ready=False
- Varanasi: source unchanged=True; v3 unchanged=True; general usability=2.87%; required media=4.27%; source ready=False
- Manali: source unchanged=True; v3 unchanged=True; general usability=0.06%; required media=0.0%; source ready=False

Deferral is field-specific: generic gates/viewpoints/urban parks without controlled-entry evidence do not get hours research; descriptions prioritize important attractions; optional websites defer. Explicit venue words recover schedule relevance when the existing category is generic heritage. No hours or rights are fabricated.
