# Real SigLIP smoke validation

Eight visually inspected, source-linked POI references versus two cross-place distractors each. All are actual locally cached POI photographs; source evidence defines the expected reference. Ranking below uses only SigLIP similarity, excluding source priors. No cloud inference.

```json
{
  "model": "google/siglip-base-patch16-224",
  "revision": "7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed",
  "device": "cpu",
  "model_load_seconds": 6.689946700003929,
  "total_seconds": 62.710573599964846,
  "inference_seconds": 12.107354199979454,
  "seconds_per_candidate": 0.5044730916658106,
  "counts": {
    "ranking_opportunities": 24,
    "processed_locally": 24,
    "failures": 0,
    "deterministic_entity_resolved": 0,
    "high_confidence_ranking": 5,
    "high_confidence_with_strong_source": 0,
    "low_relevance": 17,
    "ambiguous": 2,
    "groq_candidate_checks_needed": 24,
    "smoke_cases": 8,
    "top1_correct": 8,
    "top3_contains_correct": 8,
    "research_handoff_zero_cached_candidate_groups": 85,
    "clear_confidence_cases": 5,
    "ambiguous_cases": 2,
    "low_confidence_cases": 1,
    "incorrect_rankings": 0
  },
  "ranker_stats": {
    "ranked": 24,
    "batches": 8
  },
  "cloud_calls": {
    "groq": 0,
    "gemini": 0,
    "paid": 0
  },
  "gemini_needed": "Unknown until Groq returns unavailable/ambiguous; no live cloud calls made",
  "incremental_cloud_savings_from_siglip": 0,
  "limitations": [
    "SigLIP similarity is not calibrated identity probability.",
    "Entity-linked checks already avoided cloud before this phase.",
    "All-candidate counts are candidate checks, not measured provider requests.",
    "Top-3 in three-candidate smoke groups is a weak metric; Top-1 and margins matter.",
    "Cached candidate absence is not proof that no photograph exists on the web."
  ],
  "peak_working_set_mb": 1210.57421875,
  "thresholds": {
    "high_relevance": 0.743963748216629,
    "min_relevance": 0.07329191989265382,
    "ambiguity_margin": 0.37639855653833365
  }
}
```

Calibration is provisional; see siglip_calibration.md. Candidate LOW counts include the distractors; reference-case outcomes are five clear, two ambiguous and one low despite correct ranking.

## Albert Hall Museum — Jaipur / heritage

Expected: Entity-linked reference should outrank the explicitly unrelated cross-place distractors. Actual correct rank: 1. Top margin: 0.96421900.

| Rank | Candidate and source page | Reference | Similarity | Confidence |
|---|---|---|---:|---|
| 1 | [Albert Hall museum, Jaipur.jpg](https://commons.wikimedia.org/wiki/File:Albert_Hall_museum,_Jaipur.jpg) | True | 0.96422076 | HIGH |
| 2 | [Jaipur - Birla Temple (7122464805).jpg](https://commons.wikimedia.org/wiki/File:Jaipur_-_Birla_Temple_(7122464805).jpg) | False | 0.00000176 | LOW |
| 3 | [Bhrigu Lake by Ahmad Faiz Mustafa (4).jpg](https://commons.wikimedia.org/wiki/File:Bhrigu_Lake_by_Ahmad_Faiz_Mustafa_(4).jpg) | False | 0.00000000 | LOW |

Exact local image paths and score vectors are in siglip_real_smoke.json.

## Sisodia Rani Palace and Garden — Jaipur / heritage

Expected: Entity-linked reference should outrank the explicitly unrelated cross-place distractors. Actual correct rank: 1. Top margin: 0.94627777.

| Rank | Candidate and source page | Reference | Similarity | Confidence |
|---|---|---|---:|---|
| 1 | [Rani Sisodia Garden.jpg](https://commons.wikimedia.org/wiki/File:Rani_Sisodia_Garden.jpg) | True | 0.94627780 | HIGH |
| 2 | [Hidimba Temple Manali.jpg](https://commons.wikimedia.org/wiki/File:Hidimba_Temple_Manali.jpg) | False | 0.00000003 | LOW |
| 3 | [Bhrigu Lake by Ahmad Faiz Mustafa (4).jpg](https://commons.wikimedia.org/wiki/File:Bhrigu_Lake_by_Ahmad_Faiz_Mustafa_(4).jpg) | False | 0.00000000 | LOW |

Exact local image paths and score vectors are in siglip_real_smoke.json.

## Birla Mandir (aka The Marble Temple) — Jaipur / heritage

Expected: Entity-linked reference should outrank the explicitly unrelated cross-place distractors. Actual correct rank: 1. Top margin: 0.92783490.

| Rank | Candidate and source page | Reference | Similarity | Confidence |
|---|---|---|---:|---|
| 1 | [Jaipur - Birla Temple (7122464805).jpg](https://commons.wikimedia.org/wiki/File:Jaipur_-_Birla_Temple_(7122464805).jpg) | True | 0.92814851 | HIGH |
| 2 | [Rani Sisodia Garden.jpg](https://commons.wikimedia.org/wiki/File:Rani_Sisodia_Garden.jpg) | False | 0.00031361 | LOW |
| 3 | [Bhrigu Lake by Ahmad Faiz Mustafa (4).jpg](https://commons.wikimedia.org/wiki/File:Bhrigu_Lake_by_Ahmad_Faiz_Mustafa_(4).jpg) | False | 0.00000000 | LOW |

Exact local image paths and score vectors are in siglip_real_smoke.json.

## Galtaji — Jaipur / heritage

Expected: Entity-linked reference should outrank the explicitly unrelated cross-place distractors. Actual correct rank: 1. Top margin: 0.61786476.

| Rank | Candidate and source page | Reference | Similarity | Confidence |
|---|---|---|---:|---|
| 1 | [GaltaTempleOverview.jpg](https://commons.wikimedia.org/wiki/File:GaltaTempleOverview.jpg) | True | 0.61808825 | AMBIGUOUS |
| 2 | [Albert Hall museum, Jaipur.jpg](https://commons.wikimedia.org/wiki/File:Albert_Hall_museum,_Jaipur.jpg) | False | 0.00022349 | LOW |
| 3 | [Hidimba Temple Manali.jpg](https://commons.wikimedia.org/wiki/File:Hidimba_Temple_Manali.jpg) | False | 0.00000001 | LOW |

Exact local image paths and score vectors are in siglip_real_smoke.json.

## Kesar Kyari — Jaipur / park

Expected: Entity-linked reference should outrank the explicitly unrelated cross-place distractors. Actual correct rank: 1. Top margin: 0.13493235.

| Rank | Candidate and source page | Reference | Similarity | Confidence |
|---|---|---|---:|---|
| 1 | [Amber Palace-Kesar Kyari Garden VJC-20131017.jpg](https://commons.wikimedia.org/wiki/File:Amber_Palace-Kesar_Kyari_Garden_VJC-20131017.jpg) | True | 0.14075810 | AMBIGUOUS |
| 2 | [Jaipur - Birla Temple (7122464805).jpg](https://commons.wikimedia.org/wiki/File:Jaipur_-_Birla_Temple_(7122464805).jpg) | False | 0.00582574 | LOW |
| 3 | [Hidimba Temple Manali.jpg](https://commons.wikimedia.org/wiki/File:Hidimba_Temple_Manali.jpg) | False | 0.00000281 | LOW |

Exact local image paths and score vectors are in siglip_real_smoke.json.

## City Palace, Udaipur — Udaipur / heritage

Expected: Entity-linked reference should outrank the explicitly unrelated cross-place distractors. Actual correct rank: 1. Top margin: 0.86514483.

| Rank | Candidate and source page | Reference | Similarity | Confidence |
|---|---|---|---:|---|
| 1 | [Udaipur-Stadtpalast-04-2018-gje.jpg](https://commons.wikimedia.org/wiki/File:Udaipur-Stadtpalast-04-2018-gje.jpg) | True | 0.86983925 | HIGH |
| 2 | [Albert Hall museum, Jaipur.jpg](https://commons.wikimedia.org/wiki/File:Albert_Hall_museum,_Jaipur.jpg) | False | 0.00469442 | LOW |
| 3 | [Bhrigu Lake by Ahmad Faiz Mustafa (4).jpg](https://commons.wikimedia.org/wiki/File:Bhrigu_Lake_by_Ahmad_Faiz_Mustafa_(4).jpg) | False | 0.00000000 | LOW |

Exact local image paths and score vectors are in siglip_real_smoke.json.

## Bhrigu Lake — Manali / nature

Expected: Entity-linked reference should outrank the explicitly unrelated cross-place distractors. Actual correct rank: 1. Top margin: 0.00009683.

| Rank | Candidate and source page | Reference | Similarity | Confidence |
|---|---|---|---:|---|
| 1 | [Bhrigu Lake by Ahmad Faiz Mustafa (4).jpg](https://commons.wikimedia.org/wiki/File:Bhrigu_Lake_by_Ahmad_Faiz_Mustafa_(4).jpg) | True | 0.00009683 | LOW |
| 2 | [Jaipur - Birla Temple (7122464805).jpg](https://commons.wikimedia.org/wiki/File:Jaipur_-_Birla_Temple_(7122464805).jpg) | False | 0.00000000 | LOW |
| 3 | [Rani Sisodia Garden.jpg](https://commons.wikimedia.org/wiki/File:Rani_Sisodia_Garden.jpg) | False | 0.00000000 | LOW |

Exact local image paths and score vectors are in siglip_real_smoke.json.

## Hidimba Devi Temple, Dhungri Manali — Manali / religious

Expected: Entity-linked reference should outrank the explicitly unrelated cross-place distractors. Actual correct rank: 1. Top margin: 0.99266147.

| Rank | Candidate and source page | Reference | Similarity | Confidence |
|---|---|---|---:|---|
| 1 | [Hidimba Temple Manali.jpg](https://commons.wikimedia.org/wiki/File:Hidimba_Temple_Manali.jpg) | True | 0.99266148 | HIGH |
| 2 | [Jaipur - Birla Temple (7122464805).jpg](https://commons.wikimedia.org/wiki/File:Jaipur_-_Birla_Temple_(7122464805).jpg) | False | 0.00000000 | LOW |
| 3 | [Amber Palace-Kesar Kyari Garden VJC-20131017.jpg](https://commons.wikimedia.org/wiki/File:Amber_Palace-Kesar_Kyari_Garden_VJC-20131017.jpg) | False | 0.00000000 | LOW |

Exact local image paths and score vectors are in siglip_real_smoke.json.
