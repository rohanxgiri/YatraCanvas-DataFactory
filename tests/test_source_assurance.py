import copy
import io
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
import httpx
from PIL import Image, ImageDraw
from datafactory.ai.router import AIRouter
from datafactory.models.media_candidate import MediaCandidate
from datafactory.pipeline.media_assurance import MediaAssurance, deterministic_filter, license_allowed, local_asset
from datafactory.pipeline.media_policy import media_policy, MediaPolicy
from datafactory.pipeline.geographic_assurance import geography, coordinate_audit
from datafactory.pipeline.identity_assurance import identity_decision
from datafactory.pipeline.metadata_assurance import structured_hours, extract_hours, extract_description
from datafactory.pipeline.fallbacks import FallbackPools
from datafactory.sources.openverse import OpenverseClient
from test_ai_assurance import Fake, MEDIA, config


def picture(size=(800, 600)):
    image = Image.new("RGB", size, "blue")
    ImageDraw.Draw(image).rectangle((20, 20, 150, 190), fill="orange")
    stream = io.BytesIO()
    image.save(stream, "WEBP")
    return stream.getvalue()


def candidate(**overrides):
    fields = {"source": "Wikimedia Commons", "source_url": "https://commons.wikimedia.org/wiki/File:Landmark.jpg",
              "media_url": "https://upload.wikimedia.org/test.jpg", "title": "Landmark.jpg", "creator": "Photographer",
              "license": "CC BY-SA 4.0", "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
              "attribution": "Photographer / CC BY-SA 4.0", "width": 800, "height": 600,
              "source_confidence": 0.99, "match_method": "wikidata_p18", "original_license_verified": True}
    return MediaCandidate(**{**fields, **overrides})


@pytest.mark.parametrize("license", ["CC BY-SA 4.0", "CC-BY-2.0", "CC0", "Public Domain"])
def test_open_license_exact_allowlist(license):
    assert license_allowed(license)


@pytest.mark.parametrize("license", ["CC BY-NC 4.0", "CC BY-ND 4.0", "CC BY-SA 4.0, all rights reserved", "Unknown", ""])
def test_restrictive_license_is_rejected(license):
    assert not license_allowed(license)


@pytest.mark.parametrize("change,code", [({"width": 20}, "IMAGE_TOO_SMALL"), ({"height": 10}, "IMAGE_TOO_SMALL"),
    ({"width": 10000}, "EXTREME_ASPECT_RATIO"), ({"mime_type": "application/pdf"}, "MIME_UNSUPPORTED"),
    ({"title": "Landmark logo.png"}, "NOT_PHOTOGRAPH_CANDIDATE"), ({"title": "Landmark map.png"}, "NOT_PHOTOGRAPH_CANDIDATE"),
    ({"title": "Landmark diagram.png"}, "NOT_PHOTOGRAPH_CANDIDATE"), ({"creator": None}, "ATTRIBUTION_MISSING"),
    ({"attribution": None}, "ATTRIBUTION_MISSING"), ({"license": "CC BY-NC 4.0"}, "LICENSE_UNSUPPORTED")])
def test_filters_precede_ai(change, code):
    result = deterministic_filter(candidate(**change))
    assert not result["accepted"] and code in result["reason_codes"]


def test_corrupt_small_duplicate_and_path_escape(tmp_path):
    assert not deterministic_filter(candidate(), b"invalid")["accepted"]
    assert "ACTUAL_IMAGE_TOO_SMALL" in deterministic_filter(candidate(), picture((100, 100)))["reason_codes"]
    seen = set()
    assert deterministic_filter(candidate(), picture(), seen)["accepted"]
    assert "DUPLICATE_IMAGE" in deterministic_filter(candidate(), picture(), seen)["reason_codes"]
    assert local_asset(tmp_path, "../secret") is None


@pytest.mark.parametrize("changes,expected", [({}, "AUTO_APPLY"), ({"identity_match": False}, "REVIEW"),
    ({"decision": "REJECT", "wrong_place_risk": .9}, "REJECT"), ({"real_photograph": False}, "REVIEW"),
    ({"watermark_or_obstruction": True}, "REVIEW"), ({"identity_confidence": .6}, "REVIEW")])
def test_vision_requires_all_source_and_visual_gates(tmp_path, changes, expected):
    provider = Fake(outcome={**MEDIA, **changes})
    router = AIRouter({"city": "Jaipur"}, tmp_path, config(), [provider])
    service = MediaAssurance({"name": "Jaipur"}, router, tmp_path)
    place = {"id": "test", "name": "Amber Fort", "latitude": 27, "longitude": 76}
    result = service.assess(place, candidate(), picture())
    assert result["action"] == expected
    assert service.assess(place, candidate(source_confidence=.5), picture())["action"] != "AUTO_APPLY"


def test_openverse_original_provenance_and_unverified_license(tmp_path, monkeypatch):
    client = OpenverseClient(httpx.MockTransport(lambda r: httpx.Response(200, json={"results": [{
        "id": "123", "title": "A city landmark", "source": "flickr", "foreign_landing_url": "https://www.flickr.com/photos/a/1",
        "url": "https://live.staticflickr.com/a.jpg", "creator": "Creator", "license": "by-sa", "license_version": "4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/", "attribution": "Creator / CC BY-SA 4.0", "width": 800, "height": 600}]})))
    client.cache.cache_dir = tmp_path
    found = client.search("a landmark")
    assert found[0].source == "Openverse/flickr" and found[0].creator == "Creator"
    assert not found[0].original_license_verified
    service = MediaAssurance({}, AIRouter({}, tmp_path, config(), [Fake()]), tmp_path)
    assert service.assess({"id": "p", "name": "Landmark"}, found[0], picture())["reason_codes"] == ["ORIGINAL_SOURCE_LICENSE_UNVERIFIED"]


def test_discovery_reuses_network_cache_and_expires_negative_results(tmp_path, monkeypatch):
    import os,time
    from datafactory.utils.atomic import atomic_json
    service=MediaAssurance({"name":"Fixture"},AIRouter({},tmp_path,config(),[]),tmp_path,allow_network=True)
    p={"id":"p","name":"Landmark","latitude":26.9,"longitude":75.8}
    evidence={"wikidata_p18":"Landmark.jpg"}
    path=service._discovery_path(p,evidence)
    atomic_json(path,[candidate().model_dump()])
    monkeypatch.setattr(service.commons,"get_image_info",lambda *args: pytest.fail("Unchanged discovery must not make a source request"))
    assert service.discover(p,evidence)[0].title == "Landmark.jpg"
    assert service.cached_discovery({**p,"latitude":27.1},evidence) is None
    atomic_json(path,[])
    os.utime(path,(time.time()-3601,time.time()-3601))
    assert service.cached_discovery(p,evidence) is None


def place(qid="Q1", name="Temple", city="Jaipur", lat=26.9, lon=75.8):
    return {"id": name, "name": name, "category": "religious", "latitude": lat, "longitude": lon,
            "city": {"id": city, "state": "Rajasthan", "country": "India"}, "wikidata_id": qid}


def test_identity_corrobation_aliases_and_conflicts():
    a = place(name="Temple of Light")
    b = place(name="Jyoti Mandir", lat=26.9001)
    b["alternate_names"] = ["Temple of Light"]
    assert identity_decision(a,b)["decision"] == "SAFE_SAME_PLACE"
    assert identity_decision(a,place("Q2", "Nearby Temple", lat=26.9001))["decision"] == "SAFE_DIFFERENT_PLACE"
    assert identity_decision(a,place(city="Udaipur"))["decision"] == "SAFE_DIFFERENT_PLACE"
    assert identity_decision(place(None),place(None, lat=26.9001))["decision"] == "UNRESOLVED"
    assert identity_decision(a,place(name="Temple of Light", lat=27.1))["decision"] == "UNRESOLVED"


@pytest.mark.parametrize("offset,status", [(0.0001,"CORROBORATED"),(.002,"MINOR_VARIANCE"),(.006,"SUSPICIOUS"),(.04,"CONFLICT")])
def test_source_coordinate_distances(offset,status):
    p = place(lat=26.9)
    evidence = [{"source": src, "source_id": src, "identity_match": True, "latitude": 26.9+delta, "longitude":75.8}
                for src,delta in [("openstreetmap",0),("wikidata",offset)]]
    assert coordinate_audit(p,evidence)["status"] == status


def test_coordinate_repair_corroboration_and_region_evidence():
    p = place(lat=27.4)
    evidence = [{"source":src,"source_id":src,"identity_match":True,"latitude":26.9,"longitude":75.8} for src in ("openstreetmap","wikidata")]
    audit = coordinate_audit(p,evidence)
    assert audit["action"] == "AUTO_APPLY" and audit["replacement"]["source"] == "openstreetmap"
    city = {"id":"Jaipur","name":"Jaipur","center":[26.9,75.8],"bbox":[75.7,26.8,75.9,27.0]}
    assert geography(p,city)["status"] == "SUSPICIOUS"
    p["region_associations"] = [{"source":"wikivoyage","source_id":"guide-1","city_id":"Jaipur","relationship":"destination_listing"}]
    assert geography(p,city)["status"] == "VALID"
    assert geography(place(lat=28.6,lon=77.2),city)["status"] == "INVALID"
    assert coordinate_audit(place(),[{**evidence[0],"source":"groq"}])["status"] == "UNVERIFIED"


@pytest.mark.parametrize("hours", ["24/7", "Mo-Sa 09:30-17:00; Su off", "Mo-Fr 09:00-12:00,14:00-18:00", "09:00-17:00"])
def test_osm_hours_stay_deterministic(hours):
    assert structured_hours(hours) == hours


def test_grounded_hours_unknown_stale_and_ai_extraction(tmp_path):
    p = place()
    router = AIRouter({},tmp_path,config(),[Fake(outcome={"decision":"EXTRACTED","confidence":.97,"reason_codes":["SOURCE_TEXT"],
        "normalized":"Mo-Sa 09:30-17:00; Su off","supporting_quotes":["Monday-Saturday 09:30-17:00. Closed Sunday."]})])
    e = {"source":"wikivoyage","source_id":"listing","source_url":"https://en.wikivoyage.org/wiki/Test",
         "retrieved_at":datetime.now(timezone.utc).isoformat(), "text":"Monday-Saturday 09:30-17:00. Closed Sunday."}
    assert extract_hours(p,e,router)["action"] == "AUTO_APPLY"
    assert extract_hours(p,{**e,"retrieved_at":(datetime.now(timezone.utc)-timedelta(days=91)).isoformat()},router)["action"] == "REVIEW"
    assert extract_hours(p,{**e,"source":"groq"},router)["action"] == "UNRESOLVED"
    assert extract_hours(p,{},router)["action"] == "UNRESOLVED"
    assert extract_hours(p,{**e,"text":"Sometimes open."},router)["action"] == "REVIEW"


def test_description_is_supplied_excerpt_not_model_recollection():
    e={"source":"wikipedia","source_id":"article","text":"The museum exhibits regional art and sculpture."}
    result=extract_description(place(),e)
    assert result["action"] == "AUTO_APPLY" and result["value"] == e["text"]
    assert result["provenance"]["source"] == "wikipedia"


def test_media_policy_and_real_required_fallback_prohibition():
    assert media_policy({"tier":"core_destination","category":"food"}) == MediaPolicy.REAL_REQUIRED
    assert media_policy({"tier":"recommended","category":"cafe","prominence_score":.4}) == MediaPolicy.FALLBACK_ALLOWED
    pools=FallbackPools(Path(__file__).resolve().parents[1]/"assets/fallbacks")
    ids=[]
    for i in range(30):
        p={"id":f"yc_city_cafe_{i}","category":"cafe"}
        a=pools.choose(p)
        assert a == pools.choose(p)
        ids.append(a["id"])
    assert len(set(ids)) >= 5
    assert pools.choose({"id":"core","category":"cafe","tier":"core_destination"}) is None
    assert all(a["image_type"] == "fallback" for a in pools.assets)
