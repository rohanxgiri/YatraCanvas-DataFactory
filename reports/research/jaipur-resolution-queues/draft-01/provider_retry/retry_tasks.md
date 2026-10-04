# Jaipur — PROVIDER_RETRY

Tasks: 16

Preserve existing research. Provider diagnostics describe router context, not a separate HTTP attempt for every POI.

## Birla Mandir (aka The Marble Temple)

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:43:51.782681+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:44:15.067169+00:00"
    }
  ],
  "task_id": "research_a10d57f0ff6ab818ef4744ae",
  "place_id": "yc_in_rj_jaipur_birla_mandir_aka_the_marble_temple",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Birla Mandir (aka The Marble Temple)",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:Birla_Temple_(Jaipur).jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/f/f9/Birla_Temple_%28Jaipur%29.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "Birla_Temple_(Jaipur).jpg",
    "creator": "VAIRAGEE ABHILASH",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "attribution": "VAIRAGEE ABHILASH / Wikimedia Commons / CC BY-SA 4.0",
    "width": 4063,
    "height": 2759,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "research_import",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_a10d57f0ff6ab818ef4744ae",
    "place_id": "yc_in_rj_jaipur_birla_mandir_aka_the_marble_temple",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:Birla_Temple_(Jaipur).jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Birla Mandir (aka The Marble Temple); creator VAIRAGEE ABHILASH; license CC BY-SA 4.0."
      }
    ],
    "research_notes": "Fresh Commons replacement with a higher-resolution, explicitly CC BY-SA 4.0 photograph of Birla Temple.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:Birla_Temple_(Jaipur).jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "VAIRAGEE ABHILASH",
      "license": "CC BY-SA 4.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
      "attribution": "VAIRAGEE ABHILASH / Wikimedia Commons / CC BY-SA 4.0",
      "notes": "Fresh Commons replacement with a higher-resolution, explicitly CC BY-SA 4.0 photograph of Birla Temple."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:Birla_Temple_(Jaipur).jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/f/f9/Birla_Temple_%28Jaipur%29.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "CACHE_HIT",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.8157209753990173,
    "category_relevance": 0.0057114530354738235,
    "labels": {
      "real photograph": 9.317812327935826e-06,
      "map": 3.914608370791939e-08,
      "diagram": 3.1388940335830284e-09,
      "logo": 4.193764446824844e-09,
      "poster": 2.4204807047567556e-08,
      "document": 2.6546018716544495e-09,
      "generic landscape": 7.376723374363792e-07,
      "interior": 7.712330898357322e-07,
      "exterior landmark": 8.492969209328294e-05,
      "unrelated building": 2.1222367649897933e-06
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "AMBIGUOUS",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "726418d857992d78ce02d6d89f0822626ff1275bd18e7e86f7f6097bc1d5c8b3",
    "dimensions": [
      4063,
      2759
    ]
  },
  "download": {
    "bytes": 3605717,
    "sha256": "726418d857992d78ce02d6d89f0822626ff1275bd18e7e86f7f6097bc1d5c8b3",
    "http_status": 200
  },
  "reusable_asset": null,
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "AI_UNAVAILABLE"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## City Palace

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:43:51.782681+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:44:15.067169+00:00"
    }
  ],
  "task_id": "research_2178b190292274bcba5abdbc",
  "place_id": "yc_in_rj_jaipur_city_palace",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "City Palace",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:City_Palace,_jaipur.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/d/df/City_Palace%2C_jaipur.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "City_Palace,_jaipur.jpg",
    "creator": "Shubh77901",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "attribution": "Shubh77901 / Wikimedia Commons / CC BY-SA 4.0",
    "width": 4608,
    "height": 3456,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "research_import",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_2178b190292274bcba5abdbc",
    "place_id": "yc_in_rj_jaipur_city_palace",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:City_Palace,_jaipur.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for City Palace; creator Shubh77901; license CC BY-SA 4.0."
      }
    ],
    "research_notes": "Fresh Commons replacement with explicit CC BY-SA 4.0 licensing for City Palace, Jaipur.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:City_Palace,_jaipur.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "Shubh77901",
      "license": "CC BY-SA 4.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
      "attribution": "Shubh77901 / Wikimedia Commons / CC BY-SA 4.0",
      "notes": "Fresh Commons replacement with explicit CC BY-SA 4.0 licensing for City Palace, Jaipur."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "MPO_PRIMARY_FRAME_NORMALIZED",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:City_Palace,_jaipur.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/d/df/City_Palace%2C_jaipur.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "OK",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.8192744255065918,
    "category_relevance": 0.835308313369751,
    "labels": {
      "real photograph": 7.04397534718737e-05,
      "map": 3.038144598122017e-07,
      "diagram": 2.440549273785564e-08,
      "logo": 5.9731619650449375e-09,
      "poster": 9.918831977984155e-08,
      "document": 6.132240315537274e-08,
      "generic landscape": 2.7374076694286487e-07,
      "interior": 3.5724465305975173e-06,
      "exterior landmark": 0.0004239554691594094,
      "unrelated building": 0.0009191783028654754
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "AMBIGUOUS",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "1e6f63d92d9e58af36ac40cc3b335864205fb46710f84a1ce7b1679f8746346b",
    "dimensions": [
      1920,
      1440
    ]
  },
  "download": {
    "bytes": 4197196,
    "sha256": "5a0a0e11773c710a06bf2af9eefd832c58fb647ddcd935b62e1c99f6172fe55b",
    "http_status": 200
  },
  "reusable_asset": null,
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REJECT",
      "reason_codes": [
        "ACTUAL_MIME_UNSUPPORTED"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Jawahar Kala Kendra

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:45:20.041329+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:45:34.132852+00:00"
    }
  ],
  "task_id": "research_995c45850284bf597cc7066d",
  "place_id": "yc_in_rj_jaipur_jawahar_kala_kendra",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Jawahar Kala Kendra",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:2022_July_-_JawaharKalaKendra_Jaipur_13.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/4/41/2022_July_-_JawaharKalaKendra_Jaipur_13.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "2022 July - JawaharKalaKendra Jaipur 13.jpg",
    "creator": "Chainwit.",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "attribution": "Chainwit. / Wikimedia Commons / CC BY-SA 4.0",
    "width": 4032,
    "height": 3024,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "commons_exact_name_search",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_995c45850284bf597cc7066d",
    "place_id": "yc_in_rj_jaipur_jawahar_kala_kendra",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:2022_July_-_JawaharKalaKendra_Jaipur_13.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Jawahar Kala Kendra; creator Chainwit.; license CC BY-SA 4.0."
      }
    ],
    "research_notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:2022_July_-_JawaharKalaKendra_Jaipur_13.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "Chainwit.",
      "license": "CC BY-SA 4.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
      "attribution": "Chainwit. / Wikimedia Commons / CC BY-SA 4.0",
      "notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "EXISTING_SOURCE_METHOD_PRESERVED",
      "EXISTING_ASSET_REUSE",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:2022_July_-_JawaharKalaKendra_Jaipur_13.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/4/41/2022_July_-_JawaharKalaKendra_Jaipur_13.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "OK",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.6355026364326477,
    "category_relevance": 0.4339310824871063,
    "labels": {
      "real photograph": 2.407972715445794e-05,
      "map": 2.5270790047215996e-06,
      "diagram": 2.5853637453110423e-07,
      "logo": 3.821795768743641e-09,
      "poster": 1.7364200743941183e-07,
      "document": 4.2836237668097965e-08,
      "generic landscape": 2.8702422696369467e-06,
      "interior": 0.0008160084253177047,
      "exterior landmark": 0.0008591526420786977,
      "unrelated building": 0.0022526863031089306
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "AMBIGUOUS",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "e2e2001d3ab4bfa5806b77171a432fb6f5f6f9ccd6d227b7622477e34ee7ae81",
    "dimensions": [
      4032,
      3024
    ]
  },
  "download": {
    "bytes": 1796589,
    "sha256": "e2e2001d3ab4bfa5806b77171a432fb6f5f6f9ccd6d227b7622477e34ee7ae81",
    "http_status": 200
  },
  "reusable_asset": {
    "existing_local_path": "images/yc_in_rj_jaipur_jawahar_kala_kendra/primary.webp",
    "same_poi": true
  },
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "DUPLICATE_IMAGE"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Lake Palace

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:45:20.041329+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:45:34.132852+00:00"
    }
  ],
  "task_id": "research_c1ef13be45dbed0a005457e2",
  "place_id": "yc_in_rj_jaipur_lake_palace",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Lake Palace",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:Jal_Mahal_at_Jaipur_Rajasthan.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/a/af/Jal_Mahal_at_Jaipur_Rajasthan.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "Jal_Mahal_at_Jaipur_Rajasthan.jpg",
    "creator": "SPD2025",
    "license": "CC0 1.0",
    "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
    "attribution": "SPD2025 / Wikimedia Commons / CC0 1.0",
    "width": 3888,
    "height": 2592,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "research_import",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_c1ef13be45dbed0a005457e2",
    "place_id": "yc_in_rj_jaipur_lake_palace",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:Jal_Mahal_at_Jaipur_Rajasthan.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Lake Palace; creator SPD2025; license CC0 1.0."
      }
    ],
    "research_notes": "Replaced the incorrect Umaid Lake Palace candidate with an actual Jal Mahal photograph released under CC0.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:Jal_Mahal_at_Jaipur_Rajasthan.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "SPD2025",
      "license": "CC0 1.0",
      "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
      "attribution": "SPD2025 / Wikimedia Commons / CC0 1.0",
      "notes": "Replaced the incorrect Umaid Lake Palace candidate with an actual Jal Mahal photograph released under CC0."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "MPO_PRIMARY_FRAME_NORMALIZED",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:Jal_Mahal_at_Jaipur_Rajasthan.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/a/af/Jal_Mahal_at_Jaipur_Rajasthan.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "OK",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.04428977146744728,
    "category_relevance": 0.07172378897666931,
    "labels": {
      "real photograph": 4.742494184029056e-06,
      "map": 2.8548814157147717e-07,
      "diagram": 2.927322828583101e-09,
      "logo": 2.0233934527880137e-09,
      "poster": 1.563814500116223e-08,
      "document": 1.482059008850456e-08,
      "generic landscape": 5.339726385500398e-07,
      "interior": 6.281291007326217e-07,
      "exterior landmark": 6.0127757024019957e-05,
      "unrelated building": 9.843180123425554e-06
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "LOW",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "83556a977fad870202224de778fd3cc437b77249339035903fe8935d3e63572a",
    "dimensions": [
      1920,
      1280
    ]
  },
  "download": {
    "bytes": 5931957,
    "sha256": "2eab79e2bfa651e6802246a2260bbd4b84abac9b3ace96a9da2eb1ae09f62518",
    "http_status": 200
  },
  "reusable_asset": null,
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Patrika Gate

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:45:20.041329+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:45:34.132852+00:00"
    }
  ],
  "task_id": "research_2e1a64970981b33cc92951e3",
  "place_id": "yc_in_rj_jaipur_patrika_gate",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Patrika Gate",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:Patrika_gate_Jaipur.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/f/f3/Patrika_gate_Jaipur.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "Patrika gate Jaipur.jpg",
    "creator": "Darshanavenugopal",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "attribution": "Darshanavenugopal / Wikimedia Commons / CC BY-SA 4.0",
    "width": 5568,
    "height": 3712,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "commons_exact_name_search",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_2e1a64970981b33cc92951e3",
    "place_id": "yc_in_rj_jaipur_patrika_gate",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:Patrika_gate_Jaipur.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Patrika Gate; creator Darshanavenugopal; license CC BY-SA 4.0."
      }
    ],
    "research_notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:Patrika_gate_Jaipur.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "Darshanavenugopal",
      "license": "CC BY-SA 4.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
      "attribution": "Darshanavenugopal / Wikimedia Commons / CC BY-SA 4.0",
      "notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "EXISTING_SOURCE_METHOD_PRESERVED",
      "MPO_PRIMARY_FRAME_NORMALIZED",
      "EXISTING_ASSET_REUSE",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:Patrika_gate_Jaipur.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/f/f3/Patrika_gate_Jaipur.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "OK",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.8338294625282288,
    "category_relevance": 0.21076789498329163,
    "labels": {
      "real photograph": 4.738122152048163e-05,
      "map": 1.678487251410843e-07,
      "diagram": 1.4808496651141922e-08,
      "logo": 1.3955650857155888e-08,
      "poster": 1.4067244080706587e-07,
      "document": 1.9171588760968916e-08,
      "generic landscape": 6.043101734576339e-07,
      "interior": 4.3424137174952193e-07,
      "exterior landmark": 0.0015113422414287925,
      "unrelated building": 0.00034011679235845804
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "AMBIGUOUS",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "86900fe74e9ff3dc005fdebcf929895fe5b768ab7c73d0e890aa367ce72de5c9",
    "dimensions": [
      1920,
      1280
    ]
  },
  "download": {
    "bytes": 14814054,
    "sha256": "815d31f02bde84b77ad1d1b41e73b3ade2396fa1c289353db0321f27de16e94f",
    "http_status": 200
  },
  "reusable_asset": {
    "existing_local_path": "images/yc_in_rj_jaipur_patrika_gate/primary.webp",
    "same_poi": true
  },
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REJECT",
      "reason_codes": [
        "ACTUAL_MIME_UNSUPPORTED"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Statue Circle

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:45:20.041329+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:45:34.132852+00:00"
    }
  ],
  "task_id": "research_b77612498dba9468920c05c2",
  "place_id": "yc_in_rj_jaipur_statue_circle",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Statue Circle",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:Statue_Circle,_Jaipur_Rajasthan.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/8/8a/Statue_Circle%2C_Jaipur_Rajasthan.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "Statue Circle, Jaipur Rajasthan.jpg",
    "creator": "Jtsharma623",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "attribution": "Jtsharma623 / Wikimedia Commons / CC BY-SA 4.0",
    "width": 1294,
    "height": 1600,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "commons_exact_name_search",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_b77612498dba9468920c05c2",
    "place_id": "yc_in_rj_jaipur_statue_circle",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:Statue_Circle,_Jaipur_Rajasthan.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Statue Circle; creator Jtsharma623; license CC BY-SA 4.0."
      }
    ],
    "research_notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:Statue_Circle,_Jaipur_Rajasthan.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "Jtsharma623",
      "license": "CC BY-SA 4.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
      "attribution": "Jtsharma623 / Wikimedia Commons / CC BY-SA 4.0",
      "notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "EXISTING_SOURCE_METHOD_PRESERVED",
      "EXISTING_ASSET_REUSE",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:Statue_Circle,_Jaipur_Rajasthan.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/8/8a/Statue_Circle%2C_Jaipur_Rajasthan.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "OK",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.5495454668998718,
    "category_relevance": 0.0015010042116045952,
    "labels": {
      "real photograph": 0.000221354523091577,
      "map": 3.891861410920683e-07,
      "diagram": 6.640113525691049e-08,
      "logo": 1.8248428546030482e-07,
      "poster": 2.1241531555915572e-07,
      "document": 5.172243078277461e-08,
      "generic landscape": 7.163584814406931e-05,
      "interior": 7.157556751735683e-07,
      "exterior landmark": 0.0009977505542337894,
      "unrelated building": 3.4591968869790435e-05
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "AMBIGUOUS",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "5436c738c29c6f1f699a54332ea51b21f6a9b8c44c46d37984894449a1be393d",
    "dimensions": [
      1294,
      1600
    ]
  },
  "download": {
    "bytes": 119090,
    "sha256": "5436c738c29c6f1f699a54332ea51b21f6a9b8c44c46d37984894449a1be393d",
    "http_status": 200
  },
  "reusable_asset": {
    "existing_local_path": "images/yc_in_rj_jaipur_statue_circle/primary.webp",
    "same_poi": true
  },
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "DUPLICATE_IMAGE"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Moti Doongri Fort

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:45:20.041329+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:45:34.132852+00:00"
    }
  ],
  "task_id": "research_5f560ee9c012560327db16b8",
  "place_id": "yc_in_rj_jaipur_moti_doongri_fort",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Moti Doongri Fort",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:Moti_Doongri_Fort,_Jaipur;_January_2024.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/8/89/Moti_Doongri_Fort%2C_Jaipur%3B_January_2024.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "Moti Doongri Fort, Jaipur; January 2024.jpg",
    "creator": "Noon Plastic",
    "license": "CC BY 4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "attribution": "Noon Plastic / Wikimedia Commons / CC BY 4.0",
    "width": 4032,
    "height": 2268,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "commons_exact_name_search",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_5f560ee9c012560327db16b8",
    "place_id": "yc_in_rj_jaipur_moti_doongri_fort",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:Moti_Doongri_Fort,_Jaipur;_January_2024.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Moti Doongri Fort; creator Noon Plastic; license CC BY 4.0."
      }
    ],
    "research_notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:Moti_Doongri_Fort,_Jaipur;_January_2024.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "Noon Plastic",
      "license": "CC BY 4.0",
      "license_url": "https://creativecommons.org/licenses/by/4.0/",
      "attribution": "Noon Plastic / Wikimedia Commons / CC BY 4.0",
      "notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "EXISTING_SOURCE_METHOD_PRESERVED",
      "EXISTING_ASSET_REUSE",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:Moti_Doongri_Fort,_Jaipur;_January_2024.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/8/89/Moti_Doongri_Fort%2C_Jaipur%3B_January_2024.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "OK",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.015204392373561859,
    "category_relevance": 0.0033844474237412214,
    "labels": {
      "real photograph": 2.921158193203155e-05,
      "map": 6.551290994138981e-07,
      "diagram": 7.479131092225089e-09,
      "logo": 5.752271992065516e-09,
      "poster": 3.1261873090215886e-08,
      "document": 1.4485164179234289e-09,
      "generic landscape": 4.351112693257164e-06,
      "interior": 6.911614036653191e-07,
      "exterior landmark": 8.830131991999224e-05,
      "unrelated building": 2.283505273226183e-05
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "LOW",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "8c2d12506714e1caf48fa091a054bf244d7a7ee786579c4ff64cf75fcc55982b",
    "dimensions": [
      4032,
      2268
    ]
  },
  "download": {
    "bytes": 2015759,
    "sha256": "8c2d12506714e1caf48fa091a054bf244d7a7ee786579c4ff64cf75fcc55982b",
    "http_status": 200
  },
  "reusable_asset": {
    "existing_local_path": "images/yc_in_rj_jaipur_moti_doongri_fort/primary.webp",
    "same_poi": true
  },
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_LICENSE_UNVERIFIED"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "DUPLICATE_IMAGE"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Paanch Batti

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:45:20.041329+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:11.385740+00:00"
    }
  ],
  "task_id": "research_0d0f713f7bb780ecec39789b",
  "place_id": "yc_in_rj_jaipur_paanch_batti",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Paanch Batti",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:Panch_Batti_Circle_Jaipur_पांच_बत्ती_सर्किल_(2022-07)_02.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/8/8c/Panch_Batti_Circle_Jaipur_%E0%A4%AA%E0%A4%BE%E0%A4%82%E0%A4%9A_%E0%A4%AC%E0%A4%A4%E0%A5%8D%E0%A4%A4%E0%A5%80_%E0%A4%B8%E0%A4%B0%E0%A5%8D%E0%A4%95%E0%A4%BF%E0%A4%B2_%282022-07%29_02.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "Panch Batti Circle Jaipur पांच बत्ती सर्किल (2022-07) 02.jpg",
    "creator": "Chainwit.",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "attribution": "Chainwit. / Wikimedia Commons / CC BY-SA 4.0",
    "width": 4032,
    "height": 3024,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "commons_alt_name_search",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_0d0f713f7bb780ecec39789b",
    "place_id": "yc_in_rj_jaipur_paanch_batti",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:Panch_Batti_Circle_Jaipur_पांच_बत्ती_सर्किल_(2022-07)_02.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Paanch Batti; creator Chainwit.; license CC BY-SA 4.0."
      }
    ],
    "research_notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:Panch_Batti_Circle_Jaipur_पांच_बत्ती_सर्किल_(2022-07)_02.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "Chainwit.",
      "license": "CC BY-SA 4.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
      "attribution": "Chainwit. / Wikimedia Commons / CC BY-SA 4.0",
      "notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "EXISTING_SOURCE_METHOD_PRESERVED",
      "EXISTING_ASSET_REUSE",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:Panch_Batti_Circle_Jaipur_पांच_बत्ती_सर्किल_(2022-07)_02.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/8/8c/Panch_Batti_Circle_Jaipur_%E0%A4%AA%E0%A4%BE%E0%A4%82%E0%A4%9A_%E0%A4%AC%E0%A4%A4%E0%A5%8D%E0%A4%A4%E0%A5%80_%E0%A4%B8%E0%A4%B0%E0%A5%8D%E0%A4%95%E0%A4%BF%E0%A4%B2_%282022-07%29_02.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "OK",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.34201523661613464,
    "category_relevance": 0.037160903215408325,
    "labels": {
      "real photograph": 6.147231033537537e-05,
      "map": 6.937183911759348e-07,
      "diagram": 1.4676534654256557e-08,
      "logo": 1.8044046257159607e-08,
      "poster": 1.3421504796440331e-08,
      "document": 1.2240434443810955e-08,
      "generic landscape": 1.6192209386645118e-06,
      "interior": 6.584833727174555e-07,
      "exterior landmark": 0.00010563727846601978,
      "unrelated building": 3.7729954783571884e-05
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "AMBIGUOUS",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "29302f0f025eb01a4cafedec977cff99ba1f1329dc51e2e41a3003da12c3f699",
    "dimensions": [
      4032,
      3024
    ]
  },
  "download": {
    "bytes": 2992812,
    "sha256": "29302f0f025eb01a4cafedec977cff99ba1f1329dc51e2e41a3003da12c3f699",
    "http_status": 200
  },
  "reusable_asset": {
    "existing_local_path": "images/yc_in_rj_jaipur_paanch_batti/primary.webp",
    "same_poi": true
  },
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "DUPLICATE_IMAGE"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Sanganeri Gate

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:45:20.041329+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:11.385740+00:00"
    }
  ],
  "task_id": "research_8e55483c59e4cb6a51d8f10e",
  "place_id": "yc_in_rj_jaipur_sanganeri_gate",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Sanganeri Gate",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:Sanganeri_Gate_Jaipur.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/2/25/Sanganeri_Gate_Jaipur.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "Sanganeri Gate Jaipur.jpg",
    "creator": "Ramesh Lalwani",
    "license": "CC BY 2.0",
    "license_url": "https://creativecommons.org/licenses/by/2.0/",
    "attribution": "Ramesh Lalwani / Wikimedia Commons / CC BY 2.0",
    "width": 800,
    "height": 600,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "commons_exact_name_search",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_8e55483c59e4cb6a51d8f10e",
    "place_id": "yc_in_rj_jaipur_sanganeri_gate",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:Sanganeri_Gate_Jaipur.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Sanganeri Gate; creator Ramesh Lalwani; license CC BY 2.0."
      }
    ],
    "research_notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:Sanganeri_Gate_Jaipur.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "Ramesh Lalwani",
      "license": "CC BY 2.0",
      "license_url": "https://creativecommons.org/licenses/by/2.0/",
      "attribution": "Ramesh Lalwani / Wikimedia Commons / CC BY 2.0",
      "notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "EXISTING_SOURCE_METHOD_PRESERVED",
      "EXISTING_ASSET_REUSE",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:Sanganeri_Gate_Jaipur.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/2/25/Sanganeri_Gate_Jaipur.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "OK",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.8583414554595947,
    "category_relevance": 0.45717573165893555,
    "labels": {
      "real photograph": 5.366980258258991e-05,
      "map": 2.857324545857409e-07,
      "diagram": 1.0574236597449271e-08,
      "logo": 6.884147918384542e-09,
      "poster": 4.7525762880695765e-08,
      "document": 7.153644787649682e-09,
      "generic landscape": 6.126348495172351e-08,
      "interior": 5.997023322379391e-07,
      "exterior landmark": 0.00012287699792068452,
      "unrelated building": 3.699661829159595e-05
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "AMBIGUOUS",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "24624b0c34fbd815aa51fb270861298cda52c89b11b16b7629499db47a716443",
    "dimensions": [
      800,
      600
    ]
  },
  "download": {
    "bytes": 138945,
    "sha256": "24624b0c34fbd815aa51fb270861298cda52c89b11b16b7629499db47a716443",
    "http_status": 200
  },
  "reusable_asset": {
    "existing_local_path": "images/yc_in_rj_jaipur_sanganeri_gate/primary.webp",
    "same_poi": true
  },
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "DUPLICATE_IMAGE"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Gaitore

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:38.882874+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:59.818086+00:00"
    }
  ],
  "task_id": "research_6035e2625fd512b5152cd5fd",
  "place_id": "yc_in_rj_jaipur_gaitore",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Gaitore",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:Gaitore_Ki_Chhatriya.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/2/2d/Gaitore_Ki_Chhatriya.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "Gaitore Ki Chhatriya.jpg",
    "creator": "Imakanksha",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "attribution": "Imakanksha / Wikimedia Commons / CC BY-SA 4.0",
    "width": 3024,
    "height": 4032,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "commons_exact_name_search",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_6035e2625fd512b5152cd5fd",
    "place_id": "yc_in_rj_jaipur_gaitore",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:Gaitore_Ki_Chhatriya.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Gaitore; creator Imakanksha; license CC BY-SA 4.0."
      }
    ],
    "research_notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:Gaitore_Ki_Chhatriya.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "Imakanksha",
      "license": "CC BY-SA 4.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
      "attribution": "Imakanksha / Wikimedia Commons / CC BY-SA 4.0",
      "notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "EXISTING_SOURCE_METHOD_PRESERVED",
      "EXISTING_ASSET_REUSE",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:Gaitore_Ki_Chhatriya.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/2/2d/Gaitore_Ki_Chhatriya.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "OK",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.8108486533164978,
    "category_relevance": 0.2712068259716034,
    "labels": {
      "real photograph": 1.097819949791301e-05,
      "map": 3.6172320250216217e-08,
      "diagram": 1.3538403731416793e-09,
      "logo": 5.656352053406977e-10,
      "poster": 3.079744459455469e-09,
      "document": 3.939789827711593e-09,
      "generic landscape": 2.1818608786361438e-07,
      "interior": 5.5442882285206e-07,
      "exterior landmark": 0.00019133258319925517,
      "unrelated building": 1.594079913047608e-05
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "AMBIGUOUS",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "e9b78ae8b9c99e9a52cb037f17988d28ad3319d4e6903fdcd9b64c245eee5036",
    "dimensions": [
      3024,
      4032
    ]
  },
  "download": {
    "bytes": 1723304,
    "sha256": "e9b78ae8b9c99e9a52cb037f17988d28ad3319d4e6903fdcd9b64c245eee5036",
    "http_status": 200
  },
  "reusable_asset": {
    "existing_local_path": "images/yc_in_rj_jaipur_gaitore/primary.webp",
    "same_poi": true
  },
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "DUPLICATE_IMAGE"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Galwar Bagh

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:38.882874+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:59.818086+00:00"
    }
  ],
  "task_id": "research_1833a628ca538c58e5b52670",
  "place_id": "yc_in_rj_jaipur_galwar_bagh",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Galwar Bagh",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:A_shot_of_a_bright_tower_in_the_monkey_temple_of_jaipur.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/f/fa/A_shot_of_a_bright_tower_in_the_monkey_temple_of_jaipur.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "A shot of a bright tower in the monkey temple of jaipur.jpg",
    "creator": "Ilywpk",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "attribution": "Ilywpk / Wikimedia Commons / CC BY-SA 4.0",
    "width": 2592,
    "height": 1936,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "commons_alt_name_search",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_1833a628ca538c58e5b52670",
    "place_id": "yc_in_rj_jaipur_galwar_bagh",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:A_shot_of_a_bright_tower_in_the_monkey_temple_of_jaipur.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Galwar Bagh; creator Ilywpk; license CC BY-SA 4.0."
      }
    ],
    "research_notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:A_shot_of_a_bright_tower_in_the_monkey_temple_of_jaipur.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "Ilywpk",
      "license": "CC BY-SA 4.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
      "attribution": "Ilywpk / Wikimedia Commons / CC BY-SA 4.0",
      "notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "EXISTING_SOURCE_METHOD_PRESERVED",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:A_shot_of_a_bright_tower_in_the_monkey_temple_of_jaipur.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/f/fa/A_shot_of_a_bright_tower_in_the_monkey_temple_of_jaipur.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "CACHE_HIT",
    "model": "google/siglip-base-patch16-224",
    "relevance": 7.107921078386426e-07,
    "category_relevance": 5.35294966539368e-05,
    "labels": {
      "real photograph": 2.4008968466660008e-06,
      "map": 1.5541556308562576e-07,
      "diagram": 1.3831149558996003e-09,
      "logo": 3.583257857098232e-10,
      "poster": 9.11651820700854e-09,
      "document": 1.8616282959627029e-09,
      "generic landscape": 2.8360914257063996e-06,
      "interior": 2.4926234232225397e-07,
      "exterior landmark": 5.458000941871433e-06,
      "unrelated building": 3.0689620871271472e-06
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "LOW",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "43faa4426c033c21cb8cef19d98b14658feb84b2b7ae01a1d0aa07406960dc35",
    "dimensions": [
      2592,
      1936
    ]
  },
  "download": {
    "bytes": 1388066,
    "sha256": "43faa4426c033c21cb8cef19d98b14658feb84b2b7ae01a1d0aa07406960dc35",
    "http_status": 200
  },
  "reusable_asset": null,
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "identity_match_source_title",
        "typical_site_features_present"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Maharaniyon

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:38.882874+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:59.818086+00:00"
    }
  ],
  "task_id": "research_b33155cc53ce5b31a0ed71ba",
  "place_id": "yc_in_rj_jaipur_maharaniyon",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Maharaniyon",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:Maharaniyon_Ki_Chhatriyan.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/3/3c/Maharaniyon_Ki_Chhatriyan.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "Maharaniyon Ki Chhatriyan.jpg",
    "creator": "Sharvarism",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "attribution": "Sharvarism / Wikimedia Commons / CC BY-SA 4.0",
    "width": 5400,
    "height": 3600,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "commons_exact_name_search",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_b33155cc53ce5b31a0ed71ba",
    "place_id": "yc_in_rj_jaipur_maharaniyon",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:Maharaniyon_Ki_Chhatriyan.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Maharaniyon; creator Sharvarism; license CC BY-SA 4.0."
      }
    ],
    "research_notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:Maharaniyon_Ki_Chhatriyan.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "Sharvarism",
      "license": "CC BY-SA 4.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
      "attribution": "Sharvarism / Wikimedia Commons / CC BY-SA 4.0",
      "notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "EXISTING_SOURCE_METHOD_PRESERVED",
      "EXISTING_ASSET_REUSE",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:Maharaniyon_Ki_Chhatriyan.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/3/3c/Maharaniyon_Ki_Chhatriyan.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "OK",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.002738127950578928,
    "category_relevance": 0.04191838204860687,
    "labels": {
      "real photograph": 1.3198281521908939e-05,
      "map": 2.759861672529951e-07,
      "diagram": 2.5228363842444423e-09,
      "logo": 5.794214885668225e-09,
      "poster": 2.9283629743304118e-08,
      "document": 6.905215066410619e-09,
      "generic landscape": 3.401019625925983e-07,
      "interior": 2.050473312920076e-06,
      "exterior landmark": 5.811304799863137e-05,
      "unrelated building": 7.1629574449616484e-06
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "LOW",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "97bb635e0bc38f4c49540fe8fe126e236f39d45853a2228eed4fc0de9c12d4be",
    "dimensions": [
      5400,
      3600
    ]
  },
  "download": {
    "bytes": 18293358,
    "sha256": "97bb635e0bc38f4c49540fe8fe126e236f39d45853a2228eed4fc0de9c12d4be",
    "http_status": 200
  },
  "reusable_asset": {
    "existing_local_path": "images/yc_in_rj_jaipur_maharaniyon/primary.webp",
    "same_poi": true
  },
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "DUPLICATE_IMAGE"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Moon Gate

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:38.882874+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:59.818086+00:00"
    }
  ],
  "task_id": "research_b43d445e1d777d4686e15739",
  "place_id": "yc_in_rj_jaipur_moon_gate",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Moon Gate",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:The_Moon_Gate_(102577377).jpeg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/0/0e/The_Moon_Gate_%28102577377%29.jpeg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "The Moon Gate (102577377).jpeg",
    "creator": "Alexandre Ultré",
    "license": "CC BY-SA 3.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
    "attribution": "Alexandre Ultré / Wikimedia Commons / CC BY-SA 3.0",
    "width": 2048,
    "height": 1365,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "commons_exact_name_search",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_b43d445e1d777d4686e15739",
    "place_id": "yc_in_rj_jaipur_moon_gate",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:The_Moon_Gate_(102577377).jpeg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Moon Gate; creator Alexandre Ultré; license CC BY-SA 3.0."
      }
    ],
    "research_notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:The_Moon_Gate_(102577377).jpeg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "Alexandre Ultré",
      "license": "CC BY-SA 3.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
      "attribution": "Alexandre Ultré / Wikimedia Commons / CC BY-SA 3.0",
      "notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "CREATOR_UNICODE_CANONICALIZED",
      "EXISTING_SOURCE_METHOD_PRESERVED",
      "EXISTING_ASSET_REUSE",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:The_Moon_Gate_(102577377).jpeg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/0/0e/The_Moon_Gate_%28102577377%29.jpeg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "OK",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.002534338738769293,
    "category_relevance": 0.5674718022346497,
    "labels": {
      "real photograph": 3.3723081287462264e-06,
      "map": 4.0618667185299273e-07,
      "diagram": 1.6052961626655815e-08,
      "logo": 1.4415240112697347e-09,
      "poster": 6.551119646758252e-09,
      "document": 1.2270120919311012e-08,
      "generic landscape": 7.125282763809082e-08,
      "interior": 4.146128048887476e-06,
      "exterior landmark": 5.058693568571471e-05,
      "unrelated building": 1.535098817839753e-05
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "LOW",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "056e8a7780f2a246a79d4349ce7f1a11d27bc72220f938fadcb2b6085b34a66e",
    "dimensions": [
      2048,
      1365
    ]
  },
  "download": {
    "bytes": 705452,
    "sha256": "056e8a7780f2a246a79d4349ce7f1a11d27bc72220f938fadcb2b6085b34a66e",
    "http_status": 200
  },
  "reusable_asset": {
    "existing_local_path": "images/yc_in_rj_jaipur_moon_gate/primary.webp",
    "same_poi": true
  },
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "DUPLICATE_IMAGE"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Sun Gate

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:38.882874+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:59.818086+00:00"
    }
  ],
  "task_id": "research_167df503abe36472619baa51",
  "place_id": "yc_in_rj_jaipur_sun_gate",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Sun Gate",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:Amber_Fort_Jaipur-_Suraj_and_Sun_Gate_Entrance.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/0/07/Amber_Fort_Jaipur-_Suraj_and_Sun_Gate_Entrance.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "Amber Fort Jaipur- Suraj and Sun Gate Entrance.jpg",
    "creator": "VIJENDRASINGHISKING",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "attribution": "VIJENDRASINGHISKING / Wikimedia Commons / CC BY-SA 4.0",
    "width": 1080,
    "height": 1080,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "commons_exact_name_search",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_167df503abe36472619baa51",
    "place_id": "yc_in_rj_jaipur_sun_gate",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:Amber_Fort_Jaipur-_Suraj_and_Sun_Gate_Entrance.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Sun Gate; creator VIJENDRASINGHISKING; license CC BY-SA 4.0."
      }
    ],
    "research_notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:Amber_Fort_Jaipur-_Suraj_and_Sun_Gate_Entrance.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "VIJENDRASINGHISKING",
      "license": "CC BY-SA 4.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
      "attribution": "VIJENDRASINGHISKING / Wikimedia Commons / CC BY-SA 4.0",
      "notes": "Existing DataFactory Wikimedia Commons evidence retained; completed license metadata for import-time Commons re-verification and local/AI assurance."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "EXISTING_SOURCE_METHOD_PRESERVED",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:Amber_Fort_Jaipur-_Suraj_and_Sun_Gate_Entrance.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/0/07/Amber_Fort_Jaipur-_Suraj_and_Sun_Gate_Entrance.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "CACHE_HIT",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.009990963153541088,
    "category_relevance": 0.3573300838470459,
    "labels": {
      "real photograph": 3.04318582493579e-05,
      "map": 1.1571470395210781e-06,
      "diagram": 3.192123188000551e-08,
      "logo": 2.137497290277679e-08,
      "poster": 6.602516577913775e-08,
      "document": 7.36889944619179e-08,
      "generic landscape": 6.827243481666301e-08,
      "interior": 3.577564029910718e-06,
      "exterior landmark": 7.835199357941747e-05,
      "unrelated building": 2.231929329354898e-06
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "LOW",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "aabcc960faf8c8daa3a380a6aed82b170155cd396691bb10600fb3d210b78380",
    "dimensions": [
      1080,
      1080
    ]
  },
  "download": {
    "bytes": 145563,
    "sha256": "aabcc960faf8c8daa3a380a6aed82b170155cd396691bb10600fb3d210b78380",
    "http_status": 200
  },
  "reusable_asset": null,
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "AI_UNAVAILABLE"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Diwan-i-Am

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:38.882874+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:59.818086+00:00"
    }
  ],
  "task_id": "research_125bbd89adcf57d2adffcb00",
  "place_id": "yc_in_rj_jaipur_diwan_i_am",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Diwan-i-Am",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:Diwan-i-Am,_Amber_Palace_2017-09-02.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/2/22/Diwan-i-Am%2C_Amber_Palace_2017-09-02.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "Diwan-i-Am,_Amber_Palace_2017-09-02.jpg",
    "creator": "Lostsoul16",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "attribution": "Lostsoul16 / Wikimedia Commons / CC BY-SA 4.0",
    "width": 5184,
    "height": 3456,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "research_import",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_125bbd89adcf57d2adffcb00",
    "place_id": "yc_in_rj_jaipur_diwan_i_am",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:Diwan-i-Am,_Amber_Palace_2017-09-02.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Diwan-i-Am; creator Lostsoul16; license CC BY-SA 4.0."
      }
    ],
    "research_notes": "Fresh Commons research found an exact Diwan-i-Am photograph at Amber Palace.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:Diwan-i-Am,_Amber_Palace_2017-09-02.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "Lostsoul16",
      "license": "CC BY-SA 4.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
      "attribution": "Lostsoul16 / Wikimedia Commons / CC BY-SA 4.0",
      "notes": "Fresh Commons research found an exact Diwan-i-Am photograph at Amber Palace."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:Diwan-i-Am,_Amber_Palace_2017-09-02.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/2/22/Diwan-i-Am%2C_Amber_Palace_2017-09-02.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "CACHE_HIT",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.23681668937206268,
    "category_relevance": 0.1698591113090515,
    "labels": {
      "real photograph": 3.6368324799695984e-05,
      "map": 1.483700060589399e-07,
      "diagram": 1.0223832447309178e-08,
      "logo": 1.3417709165963743e-09,
      "poster": 1.9198228784489402e-08,
      "document": 1.0997311505889229e-08,
      "generic landscape": 3.3699569712553057e-07,
      "interior": 2.0138209038123023e-06,
      "exterior landmark": 0.0003813562507275492,
      "unrelated building": 0.00012081622116966173
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "AMBIGUOUS",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "80d53cfb8332ac8deed36f8fe279bb54ddec9a24943f306a5843d75816916e94",
    "dimensions": [
      5184,
      3456
    ]
  },
  "download": {
    "bytes": 5671201,
    "sha256": "80d53cfb8332ac8deed36f8fe279bb54ddec9a24943f306a5843d75816916e94",
    "http_status": 200
  },
  "reusable_asset": null,
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "AI_UNAVAILABLE"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```

## Ajmeri Gate

```json
{
  "resolution_state": "PROVIDER_RETRY",
  "problem_type": "ASSURANCE_HOLD",
  "resolution_reason": "VERIFIED_RESEARCH_PROVIDER_UNAVAILABLE",
  "breakdown": "PROVIDER",
  "current_research_status": "FOUND",
  "source_license_verified": true,
  "deterministic_checks_passed": true,
  "download_or_reuse_verified": true,
  "web_search_needed": false,
  "alternate_image_required": false,
  "provider_failures": [
    {
      "provider": "groq",
      "status_category": "AI_QUOTA_DEFERRED",
      "http_status": 429,
      "error_class": "HTTP_RATE_LIMIT",
      "rate_limited": true,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:38.882874+00:00"
    },
    {
      "provider": "gemini",
      "status_category": "AI_UNAVAILABLE",
      "http_status": 503,
      "error_class": "HTTP_SERVER_ERROR",
      "rate_limited": false,
      "retryable": true,
      "timestamp": "2026-10-03T17:46:59.818086+00:00"
    }
  ],
  "task_id": "research_48322e0971188a47493fb796",
  "place_id": "yc_in_rj_jaipur_ajmeri_gate",
  "type": "REAL_PRIMARY_IMAGE",
  "name": "Ajmeri Gate",
  "candidate": {
    "source": "Wikimedia Commons",
    "source_url": "https://commons.wikimedia.org/wiki/File:Ajmeri_Gate_-_Japiur_(2022)_-_img_03.jpg",
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/b/bf/Ajmeri_Gate_-_Japiur_%282022%29_-_img_03.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "title": "Ajmeri_Gate_-_Japiur_(2022)_-_img_03.jpg",
    "creator": "Chainwit.",
    "license": "CC BY 4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "attribution": "Chainwit. / Wikimedia Commons / CC BY 4.0",
    "width": 4032,
    "height": 3024,
    "mime_type": "image/jpeg",
    "related_entity_id": null,
    "commons_category": null,
    "source_confidence": 0.95,
    "match_method": "research_import",
    "original_license_verified": true
  },
  "existing_candidate_available": true,
  "research_evidence": {
    "task_id": "research_48322e0971188a47493fb796",
    "place_id": "yc_in_rj_jaipur_ajmeri_gate",
    "status": "FOUND",
    "sources": [
      {
        "url": "https://commons.wikimedia.org/wiki/File:Ajmeri_Gate_-_Japiur_(2022)_-_img_03.jpg",
        "source_id": null,
        "source_name": "Wikimedia Commons",
        "retrieved_at": "2026-10-03T15:51:32.852668Z",
        "source_text": "Wikimedia Commons file page for a photograph researched for Ajmeri Gate; creator Chainwit.; license CC BY 4.0."
      }
    ],
    "research_notes": "Fresh Commons research found an exact Ajmeri Gate photograph with camera coordinates matching the handoff location.",
    "type": "REAL_PRIMARY_IMAGE",
    "result": {
      "source_page_url": "https://commons.wikimedia.org/wiki/File:Ajmeri_Gate_-_Japiur_(2022)_-_img_03.jpg",
      "direct_media_url": null,
      "local_file": null,
      "source_provider": "Wikimedia Commons",
      "creator": "Chainwit.",
      "license": "CC BY 4.0",
      "license_url": "https://creativecommons.org/licenses/by/4.0/",
      "attribution": "Chainwit. / Wikimedia Commons / CC BY 4.0",
      "notes": "Fresh Commons research found an exact Ajmeri Gate photograph with camera coordinates matching the handoff location."
    }
  },
  "previous_attempt": {
    "status": "REVIEW",
    "reason_codes": [
      "AI_UNAVAILABLE",
      "IDENTITY_EVIDENCE_INSUFFICIENT",
      "GROQ_UNAVAILABLE",
      "GEMINI_UNAVAILABLE",
      "LICENSE_CANONICALIZED",
      "LOCAL_ASSURANCE_AMBIGUOUS"
    ],
    "source_page": "https://commons.wikimedia.org/wiki/File:Ajmeri_Gate_-_Japiur_(2022)_-_img_03.jpg",
    "direct_media_url": "https://upload.wikimedia.org/wikipedia/commons/b/bf/Ajmeri_Gate_-_Japiur_%282022%29_-_img_03.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original",
    "unmet_requirements": [],
    "media_result": {},
    "provider_status": "AI_UNAVAILABLE",
    "provider_failure_scope": "router_context",
    "assurance_run_started_at": "2026-10-03T17:43:37.974462+00:00",
    "last_attempt_timestamp": null
  },
  "siglip": {
    "status": "CACHE_HIT",
    "model": "google/siglip-base-patch16-224",
    "relevance": 0.910833477973938,
    "category_relevance": 0.38569390773773193,
    "labels": {
      "real photograph": 1.266370054509025e-05,
      "map": 1.5282698768714909e-06,
      "diagram": 1.0314892939788933e-08,
      "logo": 8.776488868988963e-09,
      "poster": 3.887435440219633e-08,
      "document": 1.0829211305463105e-08,
      "generic landscape": 2.3618464695118746e-07,
      "interior": 3.959771106565313e-07,
      "exterior landmark": 0.00025331234792247415,
      "unrelated building": 9.053816756932065e-05
    },
    "label": "uncertain",
    "non_photo_review": false,
    "supporting_evidence_only": true,
    "confidence": "AMBIGUOUS",
    "candidate_rank": 1,
    "top_margin": null
  },
  "checks": {
    "accepted": true,
    "reason_codes": [],
    "sha256": "5bbbaa341b5788fafe83bbf121c36ea082768bf1e70700eabf9efe7097a5138e",
    "dimensions": [
      4032,
      3024
    ]
  },
  "download": {
    "bytes": 2607317,
    "sha256": "5bbbaa341b5788fafe83bbf121c36ea082768bf1e70700eabf9efe7097a5138e",
    "http_status": 200
  },
  "reusable_asset": null,
  "provider_routing": [
    "groq",
    "gemini"
  ],
  "providers_with_recorded_failures": [
    "gemini",
    "groq"
  ],
  "research_history": {
    "input_sha256": "eb18ab3c449caf99d5320cbdda3c1bb4e3dbbd09d6f3fc26ead52d277a714446",
    "handoff_id": "handoff_5bc527aa3426a26aa66609b7",
    "audit_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\imports\\28cabf37897e530c349e2f91cd9ce2891f06e35ec225ec47ca0c2bb851b3ea92.json",
    "input_file": "C:\\Users\\girir\\Documents\\YatraCanvas-DataFactory\\data\\research\\import_inputs\\jaipur_image_retry_results_02.json"
  },
  "earlier_attempts": [
    {
      "status": "REVIEW",
      "reason_codes": [
        "ORIGINAL_SOURCE_METADATA_CONFLICT"
      ],
      "attempted_at": "2026-10-03T16:09:33.428690+00:00"
    },
    {
      "status": "REVIEW",
      "reason_codes": [
        "AI_UNAVAILABLE"
      ],
      "attempted_at": "2026-10-03T16:16:57.355193+00:00"
    }
  ]
}
```
