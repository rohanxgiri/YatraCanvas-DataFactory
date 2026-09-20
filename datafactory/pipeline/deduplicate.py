import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from ..pipeline.entity_resolution import CanonicalPlaceGraph


class DeduplicatedList(list):
    def __init__(self, items: List[Dict[str, Any]], graph: Any = None):
        super().__init__(items)
        self.graph = graph


def run_deduplicate(
    classified_places: List[Dict[str, Any]],
    duplicates_output_path: Path,
    city_name: str,
    state_name: str,
    country_name: str
) -> DeduplicatedList:
    """
    Multi-source canonical entity resolution and deduplication across all providers.
    Generates duplicates.jsonl and staging/entity_merges.jsonl with evidence logs.
    Returns a DeduplicatedList with .graph attached.
    """
    print(f"[Stage 9/20] Running Canonical Entity Resolution across {len(classified_places)} candidates...")
    graph = CanonicalPlaceGraph(city_name=city_name, state_name=state_name, country_name=country_name)
    canonical_places = graph.resolve(classified_places, duplicates_output_path)

    # Also save copy as entity_merges.jsonl in staging
    staging_dir = duplicates_output_path.parent
    merges_jsonl = staging_dir / "entity_merges.jsonl"
    if merges_jsonl != duplicates_output_path:
        with open(merges_jsonl, "w", encoding="utf-8") as f:
            for m in graph.merges_log:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")

    return DeduplicatedList(canonical_places, graph=graph)
