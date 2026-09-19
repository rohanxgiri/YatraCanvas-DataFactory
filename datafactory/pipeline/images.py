import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from ..config.settings import get_settings
from ..models.image import ImageMetadata, PlaceImages
from ..sources.wikimedia import WikimediaCommonsClient


def run_process_images(
    places: List[Dict[str, Any]],
    output_media_dir: Path,
    city_name: str = "",
    refresh_images: bool = False
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Download and process verified Wikimedia Commons imagery for places
    following the 5-step exact match hierarchy:
      1. exact Wikidata P18
      2. Wikivoyage listing image (Commons file)
      3. Wikidata Commons category
      4. linked Wikipedia lead image
      5. strict fallback: primary_image = null (ZERO generic fallback images)
    """
    client = WikimediaCommonsClient()
    images_manifest = {}
    places_with_images = []
    total_images_downloaded = 0

    print(f"[Stage 11/20] Resolving and verifying Wikimedia Commons imagery...")

    for p in places:
        item = dict(p)
        place_id = item["canonical_id"]
        primary_meta: Optional[ImageMetadata] = None
        gallery_metas: List[ImageMetadata] = []

        p18_file = item.get("wikidata_p18")
        wv_image = item.get("commons_image")
        commons_cat = item.get("commons_category")
        wiki_url = item.get("wikipedia_url")

        # Step 1: Wikidata P18 image
        if p18_file:
            info = client.get_image_info(p18_file)
            if info:
                primary_meta = client.download_and_process_image(
                    file_info=info,
                    place_id=place_id,
                    output_dir=output_media_dir,
                    match_method="wikidata_p18",
                    match_confidence=1.0,
                    refresh=refresh_images,
                )

        # Step 2: Wikivoyage listing image
        if not primary_meta and wv_image:
            info = client.get_image_info(wv_image)
            if info:
                primary_meta = client.download_and_process_image(
                    file_info=info,
                    place_id=place_id,
                    output_dir=output_media_dir,
                    match_method="wikivoyage_listing_image",
                    match_confidence=0.95,
                    refresh=refresh_images,
                )

        # Step 3: Commons Category lead image
        if not primary_meta and commons_cat:
            cat_files = client.search_category_images(commons_cat, limit=1)
            if cat_files:
                info = client.get_image_info(cat_files[0])
                if info:
                    primary_meta = client.download_and_process_image(
                        file_info=info,
                        place_id=place_id,
                        output_dir=output_media_dir,
                        match_method="commons_category",
                        match_confidence=0.85,
                        refresh=refresh_images,
                    )

        # Step 4: Wikipedia lead image
        if not primary_meta and wiki_url:
            lead_fn = client.get_wikipedia_lead_image(wiki_url)
            if lead_fn:
                info = client.get_image_info(lead_fn)
                if info:
                    primary_meta = client.download_and_process_image(
                        file_info=info,
                        place_id=place_id,
                        output_dir=output_media_dir,
                        match_method="wikipedia_lead_image",
                        match_confidence=0.85,
                        refresh=refresh_images,
                    )

        # Step 5: Commons search using exact canonical name + city (for core destinations)
        if not primary_meta and item.get("tier") == "core_destination" and city_name:
            searched_fn = client.search_commons_image(item.get("name", ""), city_name)
            if searched_fn:
                info = client.get_image_info(searched_fn)
                if info:
                    primary_meta = client.download_and_process_image(
                        file_info=info,
                        place_id=place_id,
                        output_dir=output_media_dir,
                        match_method="commons_exact_name_search",
                        match_confidence=0.75,
                        refresh=refresh_images,
                    )

        # Step 6: Commons search using verified alternate name + city (for core destinations)
        if not primary_meta and item.get("tier") == "core_destination" and city_name:
            for alt in item.get("alternate_names", [])[:2]:
                if alt and len(alt) > 4:
                    alt_fn = client.search_commons_image(alt, city_name)
                    if alt_fn:
                        info = client.get_image_info(alt_fn)
                        if info:
                            primary_meta = client.download_and_process_image(
                                file_info=info,
                                place_id=place_id,
                                output_dir=output_media_dir,
                                match_method="commons_alt_name_search",
                                match_confidence=0.70,
                                refresh=refresh_images,
                            )
                            if primary_meta:
                                break

        # For core destinations with commons category, optionally fetch up to 2 extra gallery images
        if primary_meta and item.get("tier") == "core_destination" and commons_cat:
            extra_files = client.search_category_images(commons_cat, limit=3)
            for ef in extra_files:
                if ef != primary_meta.original_file and len(gallery_metas) < 2:
                    e_info = client.get_image_info(ef)
                    if e_info:
                        e_meta = client.download_and_process_image(
                            file_info=e_info,
                            place_id=f"{place_id}_g{len(gallery_metas)+1}",
                            output_dir=output_media_dir,
                            match_method="commons_category_gallery",
                            match_confidence=0.80,
                            refresh=refresh_images,
                        )
                        if e_meta:
                            gallery_metas.append(e_meta)

        if primary_meta:
            total_images_downloaded += 1
            item["image_metadata"] = primary_meta.model_dump()
            item["gallery_metadata"] = [g.model_dump() for g in gallery_metas]
            images_manifest[place_id] = {
                "primary": primary_meta.model_dump(),
                "gallery": [g.model_dump() for g in gallery_metas]
            }
        else:
            # STRICT ZERO-HALLUCINATION RULE: primary_image = null if not verified
            item["image_metadata"] = None
            item["gallery_metadata"] = []

        places_with_images.append(item)

    print(f"       Verified exact images processed: {total_images_downloaded} / {len(places_with_images)} places")
    return places_with_images, images_manifest
