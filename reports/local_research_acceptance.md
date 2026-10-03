# Local intelligence and research handoff acceptance

Cached snapshots; no fresh extraction, web research or cloud inference.

| City | Hours | Images | Website | Description | Coordinates | Identity | Total | P0 zero candidates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Jaipur | 236 | 230 | 100 | 201 | 4 | 0 | 771 | 23 |
| Udaipur | 90 | 89 | 38 | 45 | 2 | 0 | 264 | 28 |
| Varanasi | 151 | 146 | 111 | 63 | 0 | 0 | 471 | 70 |
| Manali | 43 | 29 | 15 | 36 | 8 | 0 | 131 | 13 |

Total unresolved tasks: **1637**.

| City | Cached candidates examined | Valid cached files | Duplicates | Ranking opportunities | SigLIP rankings | Valid schedule strings |
|---|---:|---:|---:|---:|---:|---:|
| Jaipur | 117 | 102 | 19 | 83 | 0 | 62 |
| Udaipur | 108 | 79 | 15 | 64 | 0 | 27 |
| Varanasi | 158 | 101 | 12 | 89 | 0 | 23 |
| Manali | 11 | 11 | 0 | 11 | 0 | 12 |

Actual Groq calls: **0**; Gemini: **0**; paid calls: **0**. Measured call reduction: **0** (no new live baseline).
Local authoritative/source checks skip cloud decisions; tests demonstrate this without claiming dataset-wide savings.

## Jaipur required photographs with no saved discovered candidates

- Ajmeri Gate (`yc_in_rj_jaipur_ajmeri_gate`): P0 REAL_PRIMARY_IMAGE, `research_48322e0971188a47493fb796`.
- Alice Garg Seashell Museum (`yc_in_rj_jaipur_alice_garg_seashell_museum`): P0 REAL_PRIMARY_IMAGE, `research_67ce46dfdbb27020b2dce714`.
- Chulgiri Digamber Jain Temple (`yc_in_rj_jaipur_chulgiri_digamber_jain_temple`): P0 REAL_PRIMARY_IMAGE, `research_3b474339ecee01f77a83e6ae`.
- EleJungle- Jaipur Elephant Ride (`yc_in_rj_jaipur_elejungle_jaipur_elephant_ride`): P0 REAL_PRIMARY_IMAGE, `research_995b58ee2c0d27c96e389578`.
- Haveli (`yc_in_rj_jaipur_haveli`): P0 REAL_PRIMARY_IMAGE, `research_e2f7da77655aa4878572e0c3`.
- India gate (`yc_in_rj_jaipur_india_gate`): P0 REAL_PRIMARY_IMAGE, `research_fb6526da1eacaaf21aa3696e`.
- Iswari Minar Swarga Sali (Isarlat) (`yc_in_rj_jaipur_iswari_minar_swarga_sali_isarlat`): P0 REAL_PRIMARY_IMAGE, `research_a914a1697b1e9b4936f03b86`.
- Jawahar Kala Kendra (`yc_in_rj_jaipur_jawahar_kala_kendra`): P0 REAL_PRIMARY_IMAGE, `research_995c45850284bf597cc7066d`.

## Limitations

- Optional SigLIP/Sentence Transformers packages and weights are absent here. No download was forced; model fallback was exercised.
- Zero candidates means no saved discovered candidate in the prior assessment, not new network discovery.
- Identity counts cover published unresolved identities; quarantined/unpublished candidates are not revived or imported by name.
- No external research result was fabricated or applied to production packs. Fixtures demonstrate safe hours/media import and complete rebuild.
- Original v3 and selected source snapshot hashes stayed unchanged in all four cities.

See docs/local-research-workflow.md and reports/local_research_final.md for architecture, dependencies, tests and commands.
