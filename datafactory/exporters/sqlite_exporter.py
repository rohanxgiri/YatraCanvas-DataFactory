import sqlite3
from pathlib import Path
from typing import List
from ..models.city import CityMetadata
from ..models.place import Place


def export_sqlite(city_meta: CityMetadata, places: List[Place], output_db_path: Path) -> None:
    """
    Export canonical places and metadata to offline-ready SQLite database.
    Stores relative image file paths, place tiers, and indexes.
    """
    output_db_path.parent.mkdir(parents=True, exist_ok=True)
    if output_db_path.exists():
        output_db_path.unlink()

    conn = sqlite3.connect(output_db_path)
    cur = conn.cursor()

    # Create tables
    cur.execute("""
    CREATE TABLE cities (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        state TEXT NOT NULL,
        country TEXT NOT NULL,
        center_lat REAL NOT NULL,
        center_lon REAL NOT NULL,
        min_lon REAL NOT NULL,
        min_lat REAL NOT NULL,
        max_lon REAL NOT NULL,
        max_lat REAL NOT NULL,
        timezone TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE places (
        id TEXT PRIMARY KEY,
        city_id TEXT NOT NULL,
        name TEXT NOT NULL,
        name_hi TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT,
        category TEXT NOT NULL,
        subcategory TEXT,
        tier TEXT NOT NULL DEFAULT 'discovery',
        travel_relevance_score REAL DEFAULT 0.0,
        prominence_score REAL DEFAULT 0.0,
        recommended_visit_minutes INTEGER,
        tourism_priority REAL,
        family_friendly INTEGER,
        best_time TEXT,
        website TEXT,
        phone TEXT,
        opening_hours TEXT,
        overture_id TEXT,
        osm_id TEXT,
        wikidata_id TEXT,
        foursquare_id TEXT,
        wikivoyage_listing_id TEXT,
        quality_overall REAL,
        anomaly_score REAL DEFAULT 0.0,
        primary_image_path TEXT,
        thumbnail_image_path TEXT,
        generated_at TEXT,
        FOREIGN KEY (city_id) REFERENCES cities(id)
    );
    """)

    cur.execute("""
    CREATE TABLE place_tags (
        place_id TEXT NOT NULL,
        tag TEXT NOT NULL,
        PRIMARY KEY (place_id, tag),
        FOREIGN KEY (place_id) REFERENCES places(id)
    );
    """)

    cur.execute("""
    CREATE TABLE place_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id TEXT NOT NULL,
        original_file TEXT NOT NULL,
        local_path TEXT NOT NULL,
        thumbnail_path TEXT,
        author TEXT,
        license TEXT NOT NULL,
        license_url TEXT,
        attribution TEXT,
        match_method TEXT,
        match_confidence REAL,
        FOREIGN KEY (place_id) REFERENCES places(id)
    );
    """)

    cur.execute("""
    CREATE TABLE place_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id TEXT NOT NULL,
        source TEXT NOT NULL,
        source_id TEXT,
        retrieved_at TEXT,
        FOREIGN KEY (place_id) REFERENCES places(id)
    );
    """)

    # Insert city
    cur.execute("""
    INSERT INTO cities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        city_meta.id,
        city_meta.name,
        city_meta.state,
        city_meta.country,
        city_meta.center[0],
        city_meta.center[1],
        city_meta.bbox[0],
        city_meta.bbox[1],
        city_meta.bbox[2],
        city_meta.bbox[3],
        city_meta.timezone,
    ))

    # Insert places
    for p in places:
        primary_img = p.images.primary
        tier_val = p.tier.value if hasattr(p.tier, "value") else str(p.tier)
        cur.execute("""
        INSERT INTO places VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p.id,
            p.city.id,
            p.name,
            p.name_hi,
            p.location.latitude,
            p.location.longitude,
            p.location.address,
            p.classification.category,
            p.classification.subcategory,
            tier_val,
            p.travel_relevance_score,
            p.prominence_score,
            p.planning.recommended_visit_minutes,
            p.planning.tourism_priority,
            1 if p.planning.family_friendly else 0,
            p.planning.best_time,
            p.contact.website,
            p.contact.phone,
            p.opening_hours.raw,
            p.external_ids.overture_id,
            p.external_ids.osm_id,
            p.external_ids.wikidata_id,
            p.external_ids.foursquare_id,
            p.external_ids.wikivoyage_listing_id,
            p.quality.overall,
            p.anomaly_score,
            primary_img.local_path if primary_img else None,
            primary_img.thumbnail_path if primary_img else None,
            p.generated_at,
        ))

        # Insert tags
        for t in p.classification.tags:
            cur.execute("""
            INSERT OR IGNORE INTO place_tags (place_id, tag) VALUES (?, ?)
            """, (p.id, t))

        # Insert images
        if primary_img:
            cur.execute("""
            INSERT INTO place_images (place_id, original_file, local_path, thumbnail_path, author, license, license_url, attribution, match_method, match_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p.id,
                primary_img.original_file,
                primary_img.local_path or "",
                primary_img.thumbnail_path,
                primary_img.author,
                primary_img.license,
                primary_img.license_url,
                primary_img.attribution,
                primary_img.match_method,
                primary_img.match_confidence,
            ))

        # Insert gallery images
        for g in p.images.gallery:
            cur.execute("""
            INSERT INTO place_images (place_id, original_file, local_path, thumbnail_path, author, license, license_url, attribution, match_method, match_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p.id,
                g.original_file,
                g.local_path or "",
                g.thumbnail_path,
                g.author,
                g.license,
                g.license_url,
                g.attribution,
                g.match_method,
                g.match_confidence,
            ))

        # Insert sources
        for s in p.sources:
            cur.execute("""
            INSERT INTO place_sources (place_id, source, source_id, retrieved_at)
            VALUES (?, ?, ?, ?)
            """, (
                p.id,
                s.source,
                s.source_id,
                s.retrieved_at,
            ))

    # Create Indexes
    cur.execute("CREATE INDEX idx_places_city_id ON places(city_id);")
    cur.execute("CREATE INDEX idx_places_category ON places(category);")
    cur.execute("CREATE INDEX idx_places_tier ON places(tier);")
    cur.execute("CREATE INDEX idx_places_relevance ON places(travel_relevance_score DESC);")
    cur.execute("CREATE INDEX idx_places_coords ON places(latitude, longitude);")
    cur.execute("CREATE INDEX idx_places_priority ON places(tourism_priority DESC);")
    cur.execute("CREATE INDEX idx_place_tags_tag ON place_tags(tag);")

    conn.commit()
    conn.close()
