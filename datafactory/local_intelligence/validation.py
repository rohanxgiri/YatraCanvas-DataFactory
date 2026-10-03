"""Opt-in real model validation on cached release candidates; never calls cloud AI."""
import hashlib
import json
import time
from collections import Counter
from pathlib import Path
from .config import LocalConfig
from .duplicates import DuplicateIndex
from .media import LocalMediaRanker, SigLIPBackend
from ..models.media_candidate import MediaCandidate
from ..pipeline.media_assurance import deterministic_filter, media_signature
from ..pipeline.identity_assurance import compact_identity
from ..ai.router import digest
from ..research.export import find_pack, read_assurance, make_tasks
from ..utils.atomic import atomic_json
from ..utils.hashing import slugify


def cached_groups(names, settings):
    for name in names:
        pack = find_pack(name, settings=settings)
        city = json.loads((pack / "city.json").read_text(encoding="utf-8"))
        scope = Path(slugify(city["country"])) / slugify(city["state"]) / slugify(city["name"])
        assurance = read_assurance(pack)
        places = json.loads((pack / "places.json").read_text(encoding="utf-8"))
        missing = {t["place_id"] for t in make_tasks(places, city, pack, assurance) if t["type"] == "REAL_PRIMARY_IMAGE"}
        for place in places:
            place["_validation_missing_image"] = place["id"] in missing
            media = assurance.get(place["id"], {}).get("media", {})
            primary = place.get("images", {}).get("primary") or {}
            valid_identity = not media.get("identity_hash") or media["identity_hash"] == digest(compact_identity(place))
            valid_signature = not media.get("verification_hash") or media["verification_hash"] == media_signature(pack, primary)
            place["_validation_verified_primary"] = str(pack / primary["local_path"]) if primary.get("local_path") and media.get("verified") is True and valid_identity and valid_signature else None
            ready, seen, pool = [], set(), DuplicateIndex()
            for row in assurance.get(place["id"], {}).get("media", {}).get("candidates", []):
                if not row.get("candidate"):
                    continue
                candidate = MediaCandidate.model_validate(row["candidate"])
                if candidate.media_url in seen:
                    continue
                seen.add(candidate.media_url)
                if row.get("existing"):
                    path = pack / ((place.get("images", {}).get("primary") or {}).get("local_path") or "missing")
                else:
                    path = settings.staging_dir / scope / "assurance/downloads" / (hashlib.sha256(candidate.media_url.encode()).hexdigest() + ".bin")
                if not path.is_file() or path.stat().st_size > 20_000_000:
                    continue
                content = path.read_bytes()
                if not deterministic_filter(candidate, content)["accepted"] or pool.check(content)["duplicate"]:
                    continue
                ready.append((candidate, path))
            yield city, place, ready


def run_validation(names, output, settings, fixture=None, config=None, refresh_scores=False):
    config = config or LocalConfig(local_media_allow_download=False)
    started = time.perf_counter()
    backend = SigLIPBackend(config)
    ranker = LocalMediaRanker(settings.cache_dir / "local_media", config, backend)
    groups = list(cached_groups(names, settings))
    if fixture:
        specs = json.loads(Path(fixture).read_text(encoding="utf-8"))["cases"]
        index = {place["id"]: (city, place, candidates) for city, place, candidates in groups}
        selected = []
        for spec in specs:
            city, place, candidates = index[spec["place_id"]]
            correct = next((pair for pair in candidates if pair[0].match_method == "wikidata_p18"), None)
            if correct is None:
                raise ValueError(f"No source-linked correct reference for {place['id']}")
            wrongs = [next(pair for pair in index[pid][2] if pair[0].match_method == "wikidata_p18") for pid in spec["unrelated_place_ids"]]
            # Avoid candidate source priors: smoke ranks solely by SigLIP relevance.
            selected.append((city, place, [correct, *wrongs], correct[0].media_url))
    else:
        selected = [(city, place, candidates, None) for city, place, candidates in groups if candidates]
    rows, counts = [], Counter()
    durations = []
    for city, place, candidates, expected in selected:
        begin = time.perf_counter()
        ranked = ranker.rank(place, city, candidates, use_cache=not refresh_scores)
        durations.append(time.perf_counter() - begin)
        scored = sorted(ranked, key=lambda r: -r["local"].get("relevance", 0))
        valid = [r for r in scored if r["local"].get("status") in {"OK", "CACHE_HIT"}]
        counts["ranking_opportunities"] += len(candidates)
        counts["processed_locally"] += len(valid)
        counts["failures"] += len(candidates) - len(valid)
        group_resolved = False
        for entry in valid:
            local = entry["local"]
            qid = place.get("external_ids", {}).get("wikidata_id")
            candidate = entry["candidate"]
            strong = bool(qid and candidate.related_entity_id == qid and candidate.match_method == "wikidata_p18"
                          and candidate.source == "Wikimedia Commons" and candidate.source_confidence >= .98 and candidate.original_license_verified)
            counts["deterministic_entity_resolved"] += strong
            reused = str(entry["path"]) == place.get("_validation_verified_primary")
            counts["existing_verified_reference_reused"] += reused
            group_resolved = group_resolved or strong or reused
            counts["high_confidence_ranking"] += local.get("confidence") == "HIGH"
            counts["high_confidence_with_strong_source"] += strong and local.get("confidence") == "HIGH"
            counts["low_relevance"] += local.get("confidence") == "LOW"
            counts["ambiguous"] += local.get("confidence") in {"AMBIGUOUS", "UNCALIBRATED"}
            counts["unverified_candidate_checks_remaining"] += not strong and not reused and not local.get("non_photo_review")
        counts["candidate_groups"] += 1
        counts["groups_resolved_without_cloud"] += group_resolved
        counts["groq_required_groups"] += not group_resolved and bool(valid)
        correct_rank = next((i+1 for i,r in enumerate(scored) if r["candidate"].media_url == expected), None) if expected else None
        if expected:
            counts["smoke_cases"] += 1
            counts["top1_correct"] += correct_rank == 1
            counts["top3_contains_correct"] += correct_rank is not None and correct_rank <= 3
            counts["clear_confidence_cases"] += scored[0]["local"].get("confidence") == "HIGH"
            counts["ambiguous_cases"] += scored[0]["local"].get("confidence") == "AMBIGUOUS"
            counts["low_confidence_cases"] += scored[0]["local"].get("confidence") == "LOW"
        rows.append({"place_id":place["id"], "name":place["name"], "category":place["classification"]["category"], "city":city["name"],
                     "expected":"Entity-linked reference should outrank the explicitly unrelated cross-place distractors" if expected else None,
                     "correct_rank":correct_rank, "inference_seconds":durations[-1],
                     "top_margin":scored[0]["local"].get("relevance",0)-scored[1]["local"].get("relevance",0) if len(scored)>1 else None,
                     "candidates":[{"rank":i+1,"correct_reference":r["candidate"].media_url==expected if expected else None,
                                    "title":r["candidate"].title,"source_page":r["candidate"].source_url,"path":str(r["path"]),
                                    "match_method":r["candidate"].match_method,"local":r["local"]} for i,r in enumerate(scored)]})
    counts["research_handoff_missing_images_no_cached_candidates"] = sum(not c and p["_validation_missing_image"] for _,p,c in groups)
    counts["incorrect_rankings"] = counts["smoke_cases"] - counts["top1_correct"]
    report = {"model":config.local_media_model,"revision":config.local_media_revision,"device":config.local_media_device,
              "thresholds": {"high":config.local_media_relevance_threshold,"minimum":config.local_media_min_relevance,"ambiguity_margin":config.local_media_ambiguity_margin},
              "model_load_seconds":backend.load_seconds,"total_seconds":time.perf_counter()-started,
              "inference_seconds":sum(durations),"seconds_per_candidate":sum(durations)/counts["processed_locally"] if counts["processed_locally"] else None,
              "counts":dict(counts),"ranker_stats":dict(ranker.stats),"cloud_calls":{"groq":0,"gemini":0,"paid":0},
              "gemini_needed":"Unknown until Groq returns unavailable/ambiguous; no live cloud calls made",
              "incremental_cloud_savings_from_siglip":0,
              "limitations":["SigLIP similarity is not calibrated identity probability.","Entity-linked checks already avoided cloud before this phase.","All-candidate counts are candidate checks, not measured provider requests.","Top-3 in three-candidate smoke groups is a weak metric; Top-1 and margins matter.","Cached candidate absence is not proof that no photograph exists on the web."],"rows":rows}
    try:
        import ctypes
        from ctypes import wintypes
        class Memory(ctypes.Structure):
            _fields_ = [("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD)]+[(k,ctypes.c_size_t) for k in ("PeakWorkingSetSize","WorkingSetSize","QuotaPeakPagedPoolUsage","QuotaPagedPoolUsage","QuotaPeakNonPagedPoolUsage","QuotaNonPagedPoolUsage","PagefileUsage","PeakPagefileUsage")]
        info=Memory(); info.cb=ctypes.sizeof(info)
        ctypes.windll.kernel32.GetCurrentProcess.restype=wintypes.HANDLE
        ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Memory),wintypes.DWORD]
        if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(info),info.cb):
            report["peak_working_set_mb"]=info.PeakWorkingSetSize/1024**2
    except (AttributeError,OSError):
        pass
    atomic_json(output.with_suffix(".json"),report)
    lines=["# Real SigLIP smoke" if fixture else "# Cached media opportunities: real SigLIP", "", "No cloud inference or external research results.", "", "```json",json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2),"```", ""]
    for row in rows:
        lines += [f"## {row['name']} ({row['city']}, {row['category']})", "", f"Expected: {row['expected']}; correct reference rank: {row['correct_rank']}; top margin: {row['top_margin']}", "", "| Rank | Candidate | Reference | Similarity | Confidence |", "|---|---|---|---|---|"]
        lines += [f"| {c['rank']} | {c['title']} | {c['correct_reference']} | {c['local'].get('relevance')} | {c['local'].get('confidence')} |" for c in row['candidates']]
        lines += [""]
    output.with_suffix(".md").write_text("\n".join(lines),encoding="utf-8")
    return report
