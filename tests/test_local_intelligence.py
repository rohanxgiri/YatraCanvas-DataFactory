import io
from pathlib import Path
from collections import Counter
import pytest
from PIL import Image, ImageDraw
from datafactory.local_intelligence.config import LocalConfig
from datafactory.local_intelligence.duplicates import DuplicateIndex
from datafactory.local_intelligence.hours import validate_hours
from datafactory.local_intelligence.media import LocalMediaRanker, LABELS
from datafactory.local_intelligence.media import SigLIPBackend as ActualSigLIPBackend
from datafactory.local_intelligence.text import LocalTextSimilarity
from datafactory.models.media_candidate import MediaCandidate
from datafactory.pipeline.media_assurance import MediaAssurance
from datafactory.pipeline.identity_assurance import identity_decision
from datafactory.pipeline.geographic_assurance import geography, coordinate_audit


def photo(size=(800, 600), fmt="PNG", variant=0):
    image = Image.new("RGB", size, (45, 85, 120))
    draw = ImageDraw.Draw(image)
    w, h = size
    draw.rectangle((w*.1, h*.2, w*.65, h*.8), fill=(200, 70+variant, 40))
    draw.ellipse((w*.4, h*.05, w*.95, h*.45), fill=(10, 180, 50))
    draw.line((0, h, w, 0), fill=(240, 240, 240), width=max(1, w//40))
    stream = io.BytesIO()
    image.save(stream, fmt)
    return stream.getvalue()


def candidate(**updates):
    fields = dict(source="Wikimedia Commons", source_url="https://commons.wikimedia.org/wiki/File:Garden.jpg",
                  media_url="https://upload.wikimedia.org/garden.jpg", title="Garden photograph.jpg",
                  creator="Photographer", license="CC BY-SA 4.0", license_url="https://creativecommons.org/licenses/by-sa/4.0/",
                  attribution="Photographer / CC BY-SA 4.0", width=800, height=600,
                  source_confidence=.95, original_license_verified=True)
    return MediaCandidate(**{**fields, **updates})


class Backend:
    def __init__(self, scores=None):
        self.batches = []
        self.scores = scores

    def score(self, images, prompts):
        self.batches.append([im.size for im in images])
        return [self.scores or [index/10, .6] + [.1]*len(LABELS) for index, _ in enumerate(images, 1)]


def test_local_disabled_empty_and_unavailable(tmp_path, sample_place, sample_city_metadata, monkeypatch):
    path = tmp_path / "a.png"
    path.write_bytes(photo())
    entries = [(candidate(), path)]
    disabled = LocalMediaRanker(tmp_path / "cache", LocalConfig(local_media_enabled=False))
    assert disabled.rank(sample_place.model_dump(), sample_city_metadata.model_dump(), entries)[0]["local"]["status"] == "DISABLED"
    assert disabled.rank({}, {}, []) == []
    import datafactory.local_intelligence.media as module
    def unavailable(cfg):
        raise OSError("No cached model")
    monkeypatch.setattr(module, "SigLIPBackend", unavailable)
    ranker = LocalMediaRanker(tmp_path / "cache", LocalConfig(local_media_allow_download=False))
    assert ranker.rank(sample_place.model_dump(), sample_city_metadata.model_dump(), entries)[0]["local"]["status"] == "UNAVAILABLE"
    ranker.rank(sample_place.model_dump(), sample_city_metadata.model_dump(), entries)
    assert ranker.stats["failures"] == 1


def test_siglip_batches_order_cache_and_context(tmp_path, sample_place, sample_city_metadata):
    entries = []
    for i in range(7):
        path = tmp_path / f"{i}.png"
        path.write_bytes(photo(variant=i))
        entries.append((candidate(title=f"{i}.jpg"), path))
    backend = Backend()
    cfg = LocalConfig(local_media_batch_size=2, local_media_max_candidates=5)
    ranker = LocalMediaRanker(tmp_path / "cache", cfg, backend)
    ranked = ranker.rank(sample_place.model_dump(), sample_city_metadata.model_dump(), entries)
    assert len(ranked) == 5 and [len(batch) for batch in backend.batches] == [2, 2, 1]
    assert all(max(size) <= cfg.local_media_thumbnail_size for batch in backend.batches for size in batch)
    assert ranked[0]["candidate"].title == "1.jpg"
    ranked = ranker.rank(sample_place.model_dump(), sample_city_metadata.model_dump(), entries)
    assert all(row["local"]["status"] == "CACHE_HIT" for row in ranked)
    assert len(backend.batches) == 3
    ranker.rank(sample_place.model_dump(), {**sample_city_metadata.model_dump(), "name": "Other City"}, entries)
    assert len(backend.batches) == 6


@pytest.mark.parametrize("label,score,expected", [("map", .98, True), ("map", .3, False), ("real photograph", .98, False)])
def test_semantic_labels_are_conservative(tmp_path, sample_place, sample_city_metadata, label, score, expected):
    path = tmp_path / "a.png"
    path.write_bytes(photo())
    values = [.9, .8] + [.1]*len(LABELS)
    values[2+LABELS.index(label)] = score
    ranker = LocalMediaRanker(tmp_path / "cache", backend=Backend(values))
    row = ranker.rank(sample_place.model_dump(), sample_city_metadata.model_dump(), [(candidate(), path)], persist=False)[0]
    assert row["local"]["non_photo_review"] is expected
    assert row["local"]["supporting_evidence_only"]
    assert not (tmp_path / "cache").exists()


def test_sha_encoding_resize_and_distinct_duplicates():
    pool = DuplicateIndex()
    assert not pool.check(photo())["duplicate"]
    assert pool.check(photo())["method"] == "SHA256"
    assert pool.check(photo(fmt="JPEG"))["method"] == "PERCEPTUAL"
    assert pool.check(photo((400, 300)))["duplicate"]
    image = Image.new("RGB", (800, 600), "green")
    stream = io.BytesIO()
    image.save(stream, "PNG")
    assert not pool.check(stream.getvalue())["duplicate"]
    # Low-information images are not collapsed based only on perceptual hashes.
    assert not pool.check(photo(variant=120))["duplicate"]


@pytest.mark.parametrize("text", ["Mo-Fr 09:00-17:00; Sa 10:00-14:00; Su off", "Mo-Su 04:30-12:00,17:30-21:30", "24/7", "Su closed"])
def test_mature_hours_preserves_valid_syntax(text):
    result = validate_hours(text, "python")
    assert result["valid"] and result["schedule"] == text


@pytest.mark.parametrize("text", ["Mo-Fr 29:00-17:00", "open around nine", "", None])
def test_mature_hours_rejects_invalid(text):
    assert not validate_hours(text, "python")["valid"]


def test_fuzzy_transliteration_and_semantic_support(sample_place):
    cfg = LocalConfig(local_text_enabled=True)
    class Embeddings:
        def encode(self, texts, **kwargs):
            return [[1., 0.], [1., 0.]]
    local = LocalTextSimilarity(cfg, Embeddings())
    assert local.compare("Govind Dev Ji Temple", "Govind Devji Temple")["fuzzy"] > .8
    assert local.compare("Shri Govind Dev Ji Mandir", "Govind Dev Ji Temple")["fuzzy"] > .7
    assert local.compare("Albert Hall Museum", "Government Central Museum Jaipur")["semantic"] == 1
    a = sample_place.model_dump()
    b = {**a, "city": {**a["city"], "name": "Other City", "id": "other"}}
    assert identity_decision(a, b, text_similarity=local)["action"] == "NO_MERGE"
    b = {**a, "name": "Unrelated Aquarium", "external_ids": {}}
    assert identity_decision(a, b, text_similarity=local)["action"] == "REVIEW"


def test_same_source_identity_skips_router(sample_place):
    a = sample_place.model_dump()
    a["external_ids"]["wikidata_id"] = None
    b = {**a, "name": a["name"] + " Palace"}
    class NoCloud:
        def analyze(self, *args, **kwargs):
            raise AssertionError("Deterministic identity must skip cloud AI")
    assert identity_decision(a, b, NoCloud())["decision"] == "SAFE_SAME_PLACE"


def test_geometry_and_independent_coordinates(sample_place, sample_city_metadata):
    city = sample_city_metadata.model_dump()
    city["boundary_geometry"] = {"type": "Polygon", "coordinates": [[[75.7,26.85],[75.9,26.85],[75.9,26.95],[75.7,26.95],[75.7,26.85]]]}
    city["region_geometry"] = {"type": "Polygon", "coordinates": [[[75.5,26.5],[76.2,26.5],[76.2,27.3],[75.5,27.3],[75.5,26.5]]]}
    place = sample_place.model_dump()
    assert geography(place, city)["status"] == "VALID"
    place["location"] = {"latitude": 27.0, "longitude": 75.85}
    assert geography(place, city)["status"] == "SUSPICIOUS"
    place["region_associations"] = [{"source":"wikidata", "source_id":"Q1", "city_id":city["id"], "relationship":"travel_region"}]
    assert geography(place, city)["status"] == "VALID"
    assert geography(place, city)["municipal_geometry"]["distance_to_polygon_m"] > 0
    points = [{"source":s,"source_id":s,"identity_match":True,"latitude":27.0,"longitude":75.85} for s in ["wikidata","openstreetmap"]]
    assert coordinate_audit(place, points)["status"] == "CORROBORATED"
    assert coordinate_audit(place, points[:1])["status"] == "UNVERIFIED"
    place["location"] = {"latitude":10., "longitude":75.}
    assert geography(place, city)["status"] == "INVALID"


def test_entity_p18_and_empty_discovery_skip_cloud(tmp_path, sample_place, sample_city_metadata):
    class NoCloud:
        def analyze(self, *args, **kwargs):
            raise AssertionError("Must not call cloud AI")
    place = sample_place.model_dump()
    qid = place["external_ids"]["wikidata_id"]
    media = MediaAssurance(sample_city_metadata.model_dump(), NoCloud(), tmp_path)
    strong = candidate(match_method="wikidata_p18", related_entity_id=qid, source_confidence=.99)
    assert media.assess(place, strong, photo())["action"] == "AUTO_APPLY"
    assert media.prepare(place, []) == ([], [])
    assert media.stats["zero_candidate_handoffs"] == 1


def test_high_local_relevance_does_not_verify_identity(tmp_path, sample_place, sample_city_metadata):
    class CloudNeeded:
        def __init__(self): self.calls = 0
        def analyze(self, *args, **kwargs):
            self.calls += 1
            return {"status":"AI_UNAVAILABLE"}
    router = CloudNeeded()
    media = MediaAssurance(sample_city_metadata.model_dump(), router, tmp_path)
    result = media.assess(sample_place.model_dump(), candidate(), photo(), local={"relevance":.999,"non_photo_review":False})
    assert result["action"] == "REVIEW" and router.calls == 1


def test_text_optional_failure_and_cache():
    class Embeddings:
        def __init__(self): self.calls = 0
        def encode(self, texts, **kwargs):
            self.calls += 1
            return [[1.,0.],[.9,.1]]
    backend = Embeddings()
    local = LocalTextSimilarity(LocalConfig(local_text_enabled=True), backend)
    local.compare("Museum", "Gallery")
    assert local.compare("Museum", "Gallery")["semantic_status"] == "CACHE_HIT" and backend.calls == 1
    assert LocalTextSimilarity(LocalConfig(local_text_enabled=False)).compare("Museum", "Gallery")["semantic"] is None
    class Missing:
        def encode(self, *args, **kwargs): raise OSError("Model unavailable")
    result = LocalTextSimilarity(LocalConfig(local_text_enabled=True), Missing()).compare("Museum", "Gallery")
    assert result["semantic"] is None and result["fuzzy"] >= 0


def test_missing_javascript_parser_is_safe(monkeypatch):
    import datafactory.local_intelligence.hours as module
    module._validate.cache_clear()
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    assert validate_hours("24/7", "javascript")["status"] == "UNAVAILABLE"
    assert validate_hours("24/7", "python")["valid"]


def test_contradictory_entity_cannot_be_overridden_by_siglip(tmp_path, sample_place, sample_city_metadata):
    class NoCloud:
        def analyze(self, *args, **kwargs):
            raise AssertionError("Contradictory entity must be rejected before cloud")
    media = MediaAssurance(sample_city_metadata.model_dump(), NoCloud(), tmp_path)
    bad = candidate(related_entity_id="Q999999", match_method="wikidata_p18", source_confidence=.99)
    result = media.assess(sample_place.model_dump(), bad, photo(), local={"relevance":1.,"confidence":"HIGH"})
    assert result["action"] == "REJECT" and result["reason_codes"] == ["CONTRADICTORY_ENTITY_EVIDENCE"]


def test_calibrated_ranking_margin_is_not_identity_verification(tmp_path, sample_place, sample_city_metadata):
    paths=[]
    for i in range(2):
        p=tmp_path/f"{i}.png"; p.write_bytes(photo(variant=i)); paths.append((candidate(title=f"{i}.jpg"),p))
    cfg=LocalConfig(local_media_min_relevance=.05,local_media_relevance_threshold=.15,local_media_ambiguity_margin=.05)
    ranked=LocalMediaRanker(tmp_path/"cache",cfg,Backend()).rank(sample_place.model_dump(),sample_city_metadata.model_dump(),paths)
    assert ranked[0]["local"]["confidence"]=="HIGH" and ranked[0]["local"]["supporting_evidence_only"]
    assert ranked[0]["local"]["top_margin"]==pytest.approx(.1)


def test_siglip_backend_config_cache_and_tensor_interface(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from contextlib import nullcontext
    calls=[]
    class Tensor:
        def to(self,device): return self
        def sigmoid(self): return self
        def cpu(self): return self
        def tolist(self): return [[.8,.1]]
    class Processor:
        @classmethod
        def from_pretrained(cls,model,**kwargs):
            calls.append(("processor",model,kwargs)); return cls()
        def __call__(self,**kwargs):
            assert kwargs["padding"]=="max_length" and kwargs["return_tensors"]=="pt"
            return {"pixel_values":Tensor()}
    class Model:
        @classmethod
        def from_pretrained(cls,model,**kwargs):
            calls.append(("model",model,kwargs)); return cls()
        def to(self,device): assert device=="cpu"; return self
        def eval(self): return self
        def __call__(self,**kwargs): return SimpleNamespace(logits_per_image=Tensor())
    monkeypatch.setitem(sys.modules,"torch",SimpleNamespace(set_num_threads=lambda n:None,inference_mode=nullcontext))
    monkeypatch.setitem(sys.modules,"transformers",SimpleNamespace(AutoModel=Model,AutoProcessor=Processor))
    cfg=LocalConfig(local_media_model="fixture/model",local_media_revision="fixture-revision",local_media_model_cache=tmp_path,local_media_allow_download=False)
    backend=ActualSigLIPBackend(cfg)
    assert backend.score([Image.new("RGB",(224,224))],["a","b"])==[[.8,.1]]
    assert all(c[1]=="fixture/model" and c[2]["revision"]=="fixture-revision" and c[2]["local_files_only"] and not c[2]["trust_remote_code"] and c[2]["cache_dir"]==str(tmp_path) for c in calls)
    assert calls[1][2]["use_safetensors"]


def test_changed_model_does_not_reuse_calibrated_thresholds(tmp_path, sample_place, sample_city_metadata):
    path=tmp_path/"a.png";path.write_bytes(photo())
    cfg=LocalConfig(local_media_model="another/model")
    result=LocalMediaRanker(tmp_path/"cache",cfg,Backend()).rank(sample_place.model_dump(),sample_city_metadata.model_dump(),[(candidate(),path)])
    assert result[0]["local"]["confidence"]=="UNCALIBRATED"


def test_general_usability_cannot_hide_required_photo_gap(tmp_path, sample_place, sample_city_metadata):
    import copy
    from datafactory.pipeline.usability import usability
    place=sample_place.model_dump(mode="json")
    for field in ("local_path","thumbnail_path"):
        asset=tmp_path/place["images"]["primary"][field];asset.parent.mkdir(parents=True,exist_ok=True);asset.write_bytes(photo())
    places=[]
    for i in range(100):
        p=copy.deepcopy(place);p["id"]=f"fixture_{i}";p["external_ids"]["wikidata_id"]=None;p["tier"]="discovery";places.append(p)
    places[-1]["tier"]="core_destination";places[-1]["images"]["primary"]=None
    result=usability(places,sample_city_metadata.model_dump(),tmp_path)
    assert result["GENERAL_USABILITY"]==99 and result["REAL_REQUIRED_MEDIA_COVERAGE"]==0
    assert not result["SOURCE_DATA_READY"] and result["critical_blockers"]["CORE_MEDIA_UNRESOLVED"]==1


def test_prepare_entity_contradiction_skips_model_and_cloud(tmp_path, sample_place, sample_city_metadata):
    class NoModel:
        def score(self,*args): raise AssertionError("Contradictory source skips SigLIP")
    class NoCloud:
        def analyze(self,*args,**kwargs): raise AssertionError("Contradictory source skips cloud")
    class CachedMedia(MediaAssurance):
        def download(self,candidate): return photo()
    ranker=LocalMediaRanker(tmp_path/"scores",backend=NoModel())
    media=CachedMedia(sample_city_metadata.model_dump(),NoCloud(),tmp_path,ranker=ranker)
    ready,rejected=media.prepare(sample_place.model_dump(),[candidate(related_entity_id="Q999999")])
    assert not ready and rejected[0]["reason_codes"]==["CONTRADICTORY_ENTITY_EVIDENCE"]
