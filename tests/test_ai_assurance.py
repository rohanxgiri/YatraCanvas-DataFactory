import copy
import json
import httpx
import pytest
from datafactory.ai.config import AIConfig
from datafactory.ai.providers import GroqProvider, GeminiProvider, AIError
from datafactory.ai.router import AIRouter


MEDIA = {"decision": "ACCEPT", "confidence": 0.97, "reason_codes": ["ENTITY_CONTEXT_MATCH"],
    "identity_match": True, "identity_confidence": 0.97, "real_photograph": True,
    "landmark_prominence": 0.9, "mobile_card_suitability": 0.9, "hero_suitability": 0.9,
    "watermark_or_obstruction": False, "wrong_place_risk": 0.01}


def config():
    return AIConfig(providers={p: {"model": "test-free", "free_models": ["test-free"], "free_tier_confirmed": True,
        "endpoint": {"groq":"https://api.groq.com/openai/v1","gemini":"https://generativelanguage.googleapis.com/v1beta"}[p], "max_images": 3} for p in ["groq", "gemini"]},
        limits={"calls": 4, "vision_calls": 3, "escalations": 1, "max_retry_delay_seconds": 0,
                "min_call_interval_seconds": 0, "deferred_retry_seconds": 3600})


class Fake:
    def __init__(self, provider_id="groq", outcome=None):
        self.provider_id, self.model, self.outcome = provider_id, "test-free", outcome or copy.deepcopy(MEDIA)
        self.calls = 0
    def analyze_json(self, prompt, schema):
        self.calls += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome
    def analyze_images(self, prompt, schema, images):
        return self.analyze_json(prompt, schema)
    def health_check(self):
        return {"health": "OK"}


def test_router_primary_cache_invalidation_and_city_isolation(tmp_path):
    primary, fallback = Fake(), Fake("gemini")
    router = AIRouter({"city": "Jaipur", "state": "Rajasthan"}, tmp_path, config(), [primary, fallback])
    assert router.analyze({"id": "palace"}, "media_audit", {"qid": "Q1"}, [b"image"])["status"] == "OK"
    assert router.analyze({"id": "palace"}, "media_audit", {"qid": "Q1"}, [b"image"])["status"] == "OK"
    assert primary.calls == 1 and fallback.calls == 0 and router.stats["cache_hits"] == 1
    router.analyze({"id": "palace"}, "media_audit", {"qid": "Q2"}, [b"image"])
    assert primary.calls == 2
    other = AIRouter({"city": "Udaipur", "state": "Rajasthan"}, tmp_path, config(), [primary])
    other.analyze({"id": "palace"}, "media_audit", {"qid": "Q1"}, [b"image"])
    assert primary.calls == 3


@pytest.mark.parametrize("error", [AIError("AI_QUOTA_DEFERRED", 30), AIError("AI_TIMEOUT"), AIError("AI_UNAVAILABLE"), AIError("AI_HTTP_ERROR"), AIError("AI_RESULT_INVALID")])
def test_fallback_on_primary_failure(tmp_path, error):
    primary, fallback = Fake(outcome=error), Fake("gemini")
    router = AIRouter({"city": "x"}, tmp_path, config(), [primary, fallback])
    assert router.analyze({"id": "p"}, "media_audit", {})["provider"] == "gemini"
    assert router.stats["fallback"] == 1 and primary.calls == 1 and fallback.calls == 1


@pytest.mark.parametrize("response", [{"decision": "ACCEPT"}, {**MEDIA, "confidence": 1.5}, {**MEDIA, "identity_match": "true"}, {**MEDIA, "latitude": 27.0}])
def test_malformed_output_never_applies(tmp_path, response):
    router = AIRouter({}, tmp_path, config(), [Fake(outcome=response)])
    assert router.analyze({}, "media_audit", {})["status"] == "AI_RESULT_INVALID"


def test_disagreement_is_review(tmp_path):
    primary = Fake(outcome={**MEDIA, "confidence": 0.8})
    fallback = Fake("gemini", {**MEDIA, "decision": "REJECT"})
    router = AIRouter({}, tmp_path, config(), [primary, fallback])
    assert router.analyze({}, "media_audit", {}, important=True)["status"] == "REVIEW_AI_DISAGREEMENT"
    assert router.stats["escalations"] == 1


def test_disabled_unsupported_and_budget_defer(tmp_path):
    cfg = config()
    provider = Fake()
    cfg.enabled = False
    assert AIRouter({}, tmp_path, cfg, [provider]).analyze({}, "media_audit", {})["status"] == "AI_DISABLED"
    cfg.enabled = True
    cfg.limits["calls"] = 0
    assert AIRouter({}, tmp_path, cfg, [provider]).analyze({}, "media_audit", {})["status"] == "AI_QUOTA_DEFERRED"
    cfg.limits["calls"] = 5
    unsupported = Fake("paid")
    assert AIRouter({}, tmp_path, cfg, [unsupported]).analyze({}, "media_audit", {})["status"] == "FREE_ONLY_BLOCKED"
    assert provider.calls == 0 and unsupported.calls == 0
    assert list(tmp_path.rglob("pending/*.json"))


def test_both_unavailable_negative_cache(tmp_path):
    providers = [Fake(outcome=AIError("AI_UNAVAILABLE")), Fake("gemini", AIError("AI_QUOTA_DEFERRED", 30))]
    router = AIRouter({}, tmp_path, config(), providers)
    assert router.analyze({}, "media_audit", {})["status"] == "AI_QUOTA_DEFERRED"
    assert router.analyze({}, "media_audit", {})["status"] == "AI_QUOTA_DEFERRED"
    assert [p.calls for p in providers] == [1, 1]


def test_quota_circuit_skips_new_jobs_but_reuses_valid_cache(tmp_path):
    primary, fallback = Fake(), Fake("gemini")
    router = AIRouter({}, tmp_path, config(), [primary, fallback])
    router.analyze({"id":"cached"}, "media_audit", {})
    primary.outcome = AIError("AI_QUOTA_DEFERRED", 30)
    router.analyze({"id":"new"}, "media_audit", {})
    router.analyze({"id":"another"}, "media_audit", {})
    router.analyze({"id":"cached"}, "media_audit", {})
    assert primary.calls == 2 and fallback.calls == 2
    assert router.stats["provider_cooldown_skips"] == 1 and router.stats["cache_hits"] == 1


def test_cached_decision_reuses_without_key_or_health_network(tmp_path, monkeypatch):
    cfg = config()
    AIRouter({},tmp_path,cfg,[Fake()]).analyze({"id":"p"},"media_audit",{})
    monkeypatch.delenv("GROQ_API_KEY",raising=False)
    requests=[]
    offline = GroqProvider(cfg,httpx.MockTransport(lambda req: requests.append(req)))
    router=AIRouter({},tmp_path,cfg,[offline])
    assert router.analyze({"id":"p"},"media_audit",{})["status"] == "OK"
    assert not requests and router.stats["calls"] == 0 and router.stats["cache_hits"] == 1


def test_vendor_key_cannot_be_sent_to_configured_other_host(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY","fixture-secret")
    cfg=config(); cfg.providers["groq"]["endpoint"]="https://other.example"
    requests=[]
    provider=GroqProvider(cfg,httpx.MockTransport(lambda req: requests.append(req)))
    assert provider.health_check()["health"] == "FREE_ONLY_BLOCKED"
    assert not requests


@pytest.mark.parametrize("kind", [GroqProvider, GeminiProvider])
def test_vendor_payload_json_model_listing_and_key_redaction(monkeypatch, kind):
    monkeypatch.setenv(f"{kind.provider_id.upper()}_API_KEY", "fixture-secret-never-log")
    requests = []
    def handler(request):
        requests.append(request)
        assert "fixture-secret" not in str(request.url)
        if request.method == "GET":
            data = {"data": [{"id": "test-free"}]} if kind == GroqProvider else {"models": [{"name": "models/test-free", "supportedGenerationMethods": ["generateContent"]}]}
        else:
            body = json.loads(request.content)
            assert "tools" not in body and "grounding" not in str(body)
            data = {"choices": [{"message": {"content": json.dumps(MEDIA)}}]} if kind == GroqProvider else {"candidates": [{"content": {"parts": [{"text": json.dumps(MEDIA)}]}}]}
        return httpx.Response(200, json=data)
    provider = kind(config(), httpx.MockTransport(handler))
    assert provider.health_check()["health"] == "OK"
    assert provider.analyze_images("Evidence", {}, [b"webp"])["decision"] == "ACCEPT"
    assert len(requests) == 2
    with pytest.raises(AIError, match="AI_IMAGE_LIMIT"):
        provider.analyze_images("Evidence", {}, [b"image"]*4)


@pytest.mark.parametrize("status,code", [(429, "AI_QUOTA_DEFERRED"), (403, "AI_UNAVAILABLE"), (500, "AI_HTTP_ERROR")])
def test_vendor_errors_are_safe(monkeypatch, status, code):
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    provider = GeminiProvider(config(), httpx.MockTransport(lambda req: httpx.Response(status, headers={"retry-after": "30"}, text="do not log secret")))
    with pytest.raises(AIError) as exc:
        provider._request("GET", "/models")
    assert str(exc.value) == code and "secret" not in str(exc.value)


def test_no_paid_or_unconfirmed_model_can_execute(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "secret")
    cfg = config()
    cfg.providers["groq"]["free_tier_confirmed"] = False
    requests = []
    provider = GroqProvider(cfg, httpx.MockTransport(lambda r: requests.append(r)))
    assert provider.health_check()["health"] == "FREE_ONLY_BLOCKED"
    with pytest.raises(AIError):
        provider.analyze_json("test", {})
    assert not requests


def test_local_env_loading_is_private_and_process_overrides(tmp_path, monkeypatch):
    from datafactory.config.settings import Settings
    import datafactory.ai.config as module
    (tmp_path / ".env").write_text("GROQ_API_KEY=fixture-local-secret\nGROQ_FREE_TIER_CONFIRMED=true\nAI_MAX_CALLS_PER_CITY=2\nUNRELATED_TOKEN=ignore\n")
    (tmp_path / "config").mkdir()
    (tmp_path / "config/ai.yaml").write_text("providers:\n  groq:\n    model: test-free\n    free_models: [test-free]\nlimits: {}\n")
    monkeypatch.setattr(module, "get_settings", lambda: Settings(project_root=tmp_path))
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_FREE_TIER_CONFIRMED", raising=False)
    cfg = AIConfig.load()
    assert cfg.credentials["groq"] == "fixture-local-secret" and cfg.permitted("groq", "test-free")
    assert "fixture-local-secret" not in repr(cfg) and "UNRELATED_TOKEN" not in cfg.credentials
    monkeypatch.setenv("GROQ_API_KEY", "fixture-process-secret")
    monkeypatch.setenv("AI_MAX_CALLS_PER_CITY", "1")
    cfg = AIConfig.load()
    assert cfg.credentials["groq"] == "fixture-process-secret" and cfg.limits["calls"] == 1
