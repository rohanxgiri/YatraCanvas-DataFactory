"""Read-only review of upstream/downstream candidate identity collisions."""
import copy
import json
from collections import Counter, defaultdict
from pathlib import Path
from .entity_resolution import disambiguate_canonical_ids
from .identity_assurance import identity_decision, compact_identity
from ..utils.hashing import compute_sha256
from ..utils.atomic import atomic_json


def audit_identity_manifest(path: Path, city: dict, router, output: Path):
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Identity manifest must contain a candidate list")
    groups = defaultdict(list)
    for row in rows:
        groups[row["canonical_id"]].append(row)
    results = []
    for identifier, members in groups.items():
        if len(members) < 2:
            continue
        pairs = []
        context = {k: city[k] for k in ("id", "name", "state", "country")}
        def public_identity(row):
            # Source manifest notes, curation and review text stay local.
            return {**{k:row.get(k) for k in ("name","alternate_names","latitude","longitude","category","wikidata_id","external_ids")},
                    "alternate_names":row.get("alternate_names") or [], "id":identifier,"city":context}
        for i, a in enumerate(members):
            for b in members[i+1:]:
                a = public_identity(a)
                b = public_identity(b)
                pairs.append({"members":[compact_identity(a),compact_identity(b)], **identity_decision(a,b,router)})
        proposed = copy.deepcopy(members)
        try:
            disambiguate_canonical_ids(proposed)
            ids = [m["canonical_id"] for m in proposed]
            code = "UPSTREAM_CANONICAL_ID_BUG"
        except ValueError:
            ids, code = [], "UNRESOLVED"
        results.append({"canonical_id":identifier, "decision":code, "action":"REVIEW",
                        "members":members, "pair_assessments":pairs, "proposed_new_candidate_ids":ids,
                        "reason_codes":["MULTIPLE_SOURCE_MEMBERS_SHARE_NAME_BASED_CANONICAL_ID"],
                        "migration_applied":False})
    result = {"city":city, "source_manifest":str(path), "source_sha256":compute_sha256(path),
              "groups_found":len(results), "members_withheld":sum(len(g["members"]) for g in results),
              "auto_resolved":0, "review":len(results), "unresolved":len(results),
              "decisions":dict(Counter(g["decision"] for g in results)), "groups":results,
              "ai_usage":router.report(), "downstream_files_modified":0}
    atomic_json(output,result)
    return result
