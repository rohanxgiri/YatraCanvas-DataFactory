import re
from datetime import datetime, timezone
from .identity_assurance import compact_identity

APPROVED = {"openstreetmap", "wikivoyage", "official_website", "wikipedia", "wikidata"}


def fresh(evidence, days=90):
    dates = [evidence.get("retrieved_at"), evidence.get("check_date")]
    dates = [d for d in dates if d]
    if not dates:
        return False
    try:
        parsed = [datetime.fromisoformat(d.replace("Z", "+00:00")).replace(tzinfo=timezone.utc) for d in dates]
        age = (datetime.now(timezone.utc) - min(parsed)).total_seconds()
        return 0 <= age <= days*86400
    except (TypeError, ValueError):
        return False


def structured_hours(text):
    from ..local_intelligence.hours import validate_hours
    return text if validate_hours(text)["valid"] else None


def provenance(field, value, evidence, ai=None):
    record = {"field": field, "value": value, "source": evidence["source"],
              "source_id": evidence.get("source_id"), "source_url": evidence.get("source_url"),
              "retrieved_at": evidence.get("retrieved_at"), "original_source_text": evidence["text"],
              "check_date": evidence.get("check_date"), "confidence": 0.95, "ai_assisted": bool(ai)}
    if ai:
        record.update(provider=ai["provider"], model=ai["model"], prompt_version=ai["prompt_version"], input_hash=ai["input_hash"])
    return record


def extract_hours(place, evidence, router, freshness_days=90):
    if evidence.get("source") not in APPROVED or not evidence.get("source_id") or not evidence.get("text"):
        return {"action": "UNRESOLVED", "reason_codes": ["NO_TRUSTWORTHY_HOURS_SOURCE"]}
    if not fresh(evidence, freshness_days):
        return {"action": "REVIEW", "reason_codes": ["HOURS_SOURCE_STALE_OR_UNDATED"], "evidence": evidence}
    raw = evidence["text"]
    normalized = structured_hours(raw)
    ai = None
    if normalized is None:
        ai = router.analyze(compact_identity(place), "hours_extract", evidence)
        if ai["status"] != "OK":
            return {"action": "UNRESOLVED", "reason_codes": [ai["status"]], "ai": ai}
        result = ai["result"]
        quotes = result["supporting_quotes"]
        normalized = structured_hours(result.get("normalized") or "")
        # Require exact source quotations, source time tokens, and explicit weekday evidence.
        times = set(re.findall(r"\d{1,2}:\d{2}", normalized or ""))
        source_times = set(re.findall(r"\d{1,2}:\d{2}", raw))
        source_days = {"Mo": "monday", "Tu": "tuesday", "We": "wednesday", "Th": "thursday", "Fr": "friday", "Sa": "saturday", "Su": "sunday"}
        days = set(re.findall(r"Mo|Tu|We|Th|Fr|Sa|Su", normalized or ""))
        if (result["decision"] != "EXTRACTED" or result["confidence"] < 0.95 or not normalized or normalized == "24/7"
            or not quotes or not all(q in raw for q in quotes) or not times.issubset(source_times)
            or not all(source_days[d] in raw.lower() or d in raw for d in days)):
            return {"action": "REVIEW", "reason_codes": ["HOURS_EXTRACTION_NOT_CORROBORATED"], "ai": ai}
    value = {"raw": raw, "normalized": normalized, "source": evidence["source"],
             "retrieved_at": evidence.get("retrieved_at"), "confidence": 0.95, "verified": True, "conflicts": []}
    return {"action": "AUTO_APPLY", "value": value, "provenance": provenance("opening_hours", value, evidence, ai), "reason_codes": ["SOURCE_GROUNDED_SCHEDULE"]}


def extract_description(place, evidence, router=None):
    if evidence.get("source") not in APPROVED or not evidence.get("source_id") or not evidence.get("text"):
        return {"action": "UNRESOLVED", "reason_codes": ["NO_TRUSTWORTHY_DESCRIPTION_SOURCE"]}
    text = evidence["text"].strip()
    # Exact source excerpts are sufficient; never spend inference merely to rewrite prose.
    if "{{" not in text and "[[" not in text:
        end = min(len(text), 450)
        if end < len(text):
            end = text.rfind(".", 100, end) + 1
        if end >= 15:
            value = text[:end]
            return {"action": "AUTO_APPLY", "value": value, "provenance": provenance("description", value, evidence), "reason_codes": ["EXACT_SOURCE_EXCERPT"]}
    if router is None:
        return {"action": "REVIEW", "reason_codes": ["SOURCE_TEXT_NEEDS_EXTRACTION"]}
    ai = router.analyze(compact_identity(place), "description_extract", {**evidence, "text": text[:1800]})
    if ai["status"] != "OK":
        return {"action": "UNRESOLVED", "reason_codes": [ai["status"]], "ai": ai}
    result = ai["result"]
    description = result.get("description") or ""
    sentences = [s.strip() for s in re.split(r"(?<=\.)\s+", description) if s.strip()]
    if (result["decision"] == "EXTRACTED" and result["confidence"] >= 0.95 and 15 <= len(description) <= 500
        and sentences and all(s in text for s in sentences)
        and result["supporting_quotes"] and all(q in text for q in result["supporting_quotes"])):
        return {"action": "AUTO_APPLY", "value": description, "provenance": provenance("description", description, evidence, ai), "reason_codes": ["SOURCE_GROUNDED_EXTRACTIVE_SUMMARY"]}
    return {"action": "REVIEW", "reason_codes": ["DESCRIPTION_FACT_SUPPORT_UNVERIFIED"], "ai": ai}
