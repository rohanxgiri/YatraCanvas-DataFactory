from ..utils.text import fuzzy_name_similarity, normalize_name
from .config import LocalConfig


class LocalTextSimilarity:
    def __init__(self, config=None, backend=None):
        self.config = config or LocalConfig()
        self.backend, self.unavailable = backend, False
        self.cache = {}

    def compare(self, left: str, right: str):
        result = {"fuzzy": fuzzy_name_similarity(left, right), "semantic": None,
                  "semantic_status": "DISABLED" if not self.config.local_text_enabled else "UNAVAILABLE"}
        if not self.config.local_text_enabled or self.unavailable:
            return result
        key = (normalize_name(left), normalize_name(right))
        if key in self.cache:
            return {**result, "semantic": self.cache[key], "semantic_status": "CACHE_HIT"}
        try:
            if self.backend is None:
                from sentence_transformers import SentenceTransformer
                self.backend = SentenceTransformer(self.config.local_text_model, device="cpu",
                    local_files_only=not self.config.local_text_allow_download, trust_remote_code=False)
            vectors = self.backend.encode([left[:512], right[:512]], normalize_embeddings=True)
            value = float(sum(float(a) * float(b) for a, b in zip(vectors[0], vectors[1])))
            if len(self.cache) >= 2048:
                self.cache.clear()
            self.cache[key] = value
            return {**result, "semantic": value, "semantic_status": "OK"}
        except Exception:
            self.unavailable = True
            return result
