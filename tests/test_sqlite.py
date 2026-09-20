import sqlite3
from pathlib import Path
from datafactory.exporters.sqlite_exporter import export_sqlite


def test_sqlite_export_and_query(tmp_path, sample_city_metadata, sample_place):
    db_path = tmp_path / "test_yatracanvas.db"

    export_sqlite(sample_city_metadata, [sample_place], db_path)

    assert db_path.exists()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Verify city table
    cur.execute("SELECT name, state, country FROM cities WHERE id = ?", (sample_city_metadata.id,))
    city_row = cur.fetchone()
    assert city_row == ("Jaipur", "Rajasthan", "India")

    # Verify places table
    cur.execute("SELECT id, name, category, recommended_visit_minutes, primary_image_path FROM places WHERE id = ?", (sample_place.id,))
    place_row = cur.fetchone()
    assert place_row[0] == "yc_in_rj_jaipur_hawa_mahal"
    assert place_row[1] == "Hawa Mahal"
    assert place_row[2] == "heritage"
    assert place_row[3] == 60
    assert place_row[4] == "images/yc_in_rj_jaipur_hawa_mahal/primary.webp"

    # Verify place_tags table
    cur.execute("SELECT tag FROM place_tags WHERE place_id = ?", (sample_place.id,))
    tags = [r[0] for r in cur.fetchall()]
    assert "architecture" in tags
    assert "heritage" in tags

    # Verify place_images table
    cur.execute("SELECT original_file, license FROM place_images WHERE place_id = ?", (sample_place.id,))
    img_row = cur.fetchone()
    assert img_row[0] == "Hawa_Mahal_Jaipur.jpg"
    assert img_row[1] == "CC BY-SA 4.0"

    conn.close()
