"""Bounded SigLIP ranking; scores are supporting evidence, not fact verification."""
import hashlib
import json
import time
from collections import Counter
from pathlib import Path
from PIL import Image, ImageOps
from ..utils.atomic import atomic_json
from ..utils.hashing import compute_sha256
from .config import LocalConfig


LABELS = ("real photograph", "map", "diagram", "logo", "poster", "document",
          "generic landscape", "interior", "exterior landmark", "unrelated building")


class SigLIPBackend:
    def __init__(self, config):
        started = time.perf_counter()
        import torch
        from transformers import AutoModel, AutoProcessor
        self.torch = torch
        if config.local_media_device == "cpu":
            torch.set_num_threads(config.local_media_cpu_threads)
        from ..config.settings import get_settings
        self.cache_dir = config.local_media_model_cache or get_settings().cache_dir / "models"
        args = dict(revision=config.local_media_revision,
                    cache_dir=str(self.cache_dir), local_files_only=not config.local_media_allow_download, trust_remote_code=False)
        self.processor = AutoProcessor.from_pretrained(config.local_media_model, use_fast=False, **args)
        self.model = AutoModel.from_pretrained(config.local_media_model, use_safetensors=True, **args).to(config.local_media_device).eval()
        self.device = config.local_media_device
        self.load_seconds = time.perf_counter() - started

    def score(self, images, prompts):
        inputs = self.processor(text=prompts, images=images, padding="max_length", return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with self.torch.inference_mode():
            return self.model(**inputs).logits_per_image.sigmoid().cpu().tolist()


class LocalMediaRanker:
    def __init__(self, cache_dir: Path, config=None, backend=None):
        self.config = config or LocalConfig()
        self.cache_dir, self.backend = cache_dir, backend
        self.unavailable = False
        self.stats = Counter()
        self.last_error = None

    def prompts(self, place, city):
        category = place.get("category") or place.get("classification", {}).get("category", "attraction")
        return [f"photograph of {place['name']} {city['name']} {city.get('state', '')} {city.get('country', '')}",
                f"photograph of a {category} in {city['name']}"] + [f"an image of a {label}" for label in LABELS]

    def rank(self, place, city, candidates, *, persist=True):
        """Candidates are (MediaCandidate, validated local analysis/original path)."""
        candidates = list(candidates)[:self.config.local_media_max_candidates]
        if not candidates or not self.config.local_media_enabled:
            return [{"candidate": c, "path": p, "local": {"status": "DISABLED"}} for c, p in candidates]
        prompts = self.prompts(place, city)
        ranked, pending = [], []
        for candidate, path in candidates:
            entry = {"candidate": candidate, "path": path, "local": {"status": "UNAVAILABLE"}}
            identity = json.dumps([self.config.local_media_model, self.config.local_media_revision,
                                   self.config.local_media_thumbnail_size, prompts], sort_keys=True)
            try:
                file_hash = compute_sha256(Path(path))
            except OSError:
                entry["local"]["status"] = "IMAGE_UNAVAILABLE"
                ranked.append(entry)
                continue
            key = hashlib.sha256((identity + file_hash).encode()).hexdigest()
            cache = self.cache_dir / f"{key}.json"
            try:
                scores = json.loads(cache.read_text(encoding="utf-8"))["scores"]
                if len(scores) != len(prompts) or any(not isinstance(v, (int, float)) or not 0 <= v <= 1 for v in scores):
                    raise ValueError("Invalid scores")
                self.stats["cache_hits"] += 1
                entry["local"] = self._result(scores, "CACHE_HIT")
            except (OSError, ValueError, KeyError, TypeError):
                pending.append((entry, cache))
            ranked.append(entry)
        if pending and not self.unavailable:
            try:
                if self.backend is None:
                    self.backend = SigLIPBackend(self.config)
                for offset in range(0, len(pending), self.config.local_media_batch_size):
                    batch = pending[offset:offset+self.config.local_media_batch_size]
                    images = []
                    try:
                        for entry, _ in batch:
                            with Image.open(entry["path"]) as original:
                                if original.width * original.height > 40_000_000:
                                    raise ValueError("Image decode budget")
                                original.draft("RGB", (self.config.local_media_thumbnail_size,)*2)
                                image = ImageOps.exif_transpose(original).convert("RGB")
                                image.thumbnail((self.config.local_media_thumbnail_size,)*2)
                                images.append(image)
                        scores = self.backend.score(images, prompts)
                        if len(scores) != len(batch):
                            raise ValueError("Invalid model batch")
                        for (entry, cache), values in zip(batch, scores):
                            if len(values) != len(prompts) or any(not 0 <= v <= 1 for v in values):
                                raise ValueError("Invalid model scores")
                            entry["local"] = self._result(values, "OK")
                            self.stats["ranked"] += 1
                            if persist:
                                atomic_json(cache, {"scores": values, "model": self.config.local_media_model})
                        self.stats["batches"] += 1
                    finally:
                        for image in images:
                            image.close()
            except Exception as exc:
                self.unavailable = True
                self.stats["failures"] += 1
                self.last_error = f"{type(exc).__name__}: {exc}"
        # Authoritative identity evidence always sorts first.
        ranked = sorted(ranked, key=lambda row: (
            row["candidate"].match_method != "wikidata_p18",
            -row["local"].get("relevance", 0), -row["candidate"].source_confidence))
        scored = sorted((r for r in ranked if r["local"].get("status") in {"OK", "CACHE_HIT"}), key=lambda r: -r["local"]["relevance"])
        for i, row in enumerate(scored):
            score = row["local"]["relevance"]
            margin = score - scored[1]["local"]["relevance"] if i == 0 and len(scored) > 1 else None
            cfg = self.config
            confidence = "UNCALIBRATED"
            if all(v is not None for v in (cfg.local_media_min_relevance, cfg.local_media_relevance_threshold, cfg.local_media_ambiguity_margin)):
                confidence = "LOW" if score < cfg.local_media_min_relevance else "HIGH" if i == 0 and margin is not None and score >= cfg.local_media_relevance_threshold and margin >= cfg.local_media_ambiguity_margin else "AMBIGUOUS"
            row["local"].update(confidence=confidence, candidate_rank=i+1, top_margin=margin)
        return ranked

    def _result(self, scores, status):
        labels = dict(zip(LABELS, scores[2:]))
        label = max(labels, key=labels.get)
        runner = sorted(labels.values(), reverse=True)[1]
        confident = labels[label] >= self.config.local_media_high_threshold and labels[label] - runner >= self.config.local_media_label_margin
        return {"status": status, "model": self.config.local_media_model, "relevance": scores[0],
                "category_relevance": scores[1], "labels": labels, "label": label if confident else "uncertain",
                "non_photo_review": confident and label in {"map", "diagram", "logo", "poster", "document"},
                "supporting_evidence_only": True}
