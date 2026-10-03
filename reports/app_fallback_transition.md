# App fallback transition

The YatraCanvas app supplies fallback presentation. Factory artwork is disabled by default. New packs leave missing photos as images.primary=null and retain authentic photos and verified human choices. Source snapshots, app files and City Lab files were preserved. No AI or source network calls were made.

Strict pack usability below measures bundled media only. App fallback rendering is separate and is not counted as verified source photography. Required real-photo blockers are unchanged.

| City | Artwork removed | Missing primary / app fallback | Strict pack usable % | Required photos unresolved |
|---|---:|---:|---:|---:|
| Manali | 1688 | 1690 | 0.06 | 13 |
| Jaipur | 626 | 644 | 1.17 | 50 |
| Udaipur | 267 | 290 | 0.93 | 54 |
| Varanasi | 226 | 278 | 2.87 | 112 |

All exports passed schema/checksum/JSONL/Parquet/SQLite consistency and local retained-image validation. They remain drafts with SOURCE_DATA_READY=false.

Current output packs:

- Manali: `C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\himachal_pradesh\manali\v3-app-fallbacks`
- Jaipur: `C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\rajasthan\jaipur\v3-app-fallbacks`
- Udaipur: `C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\rajasthan\udaipur\v3-app-fallbacks`
- Varanasi: `C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\uttar_pradesh\varanasi\v3-app-fallbacks`
