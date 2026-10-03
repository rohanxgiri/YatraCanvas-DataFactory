# Local AI and research checkpoint — 2026-10-03

Recovery tag: `checkpoint/local-ai-research-2026-10-03`.

This checkpoint preserves the current DataFactory implementation, configuration,
tests, validation reports, generated research exports and handoff registry before
external research results are imported. Existing release snapshots remain intact.

Validated state:

- Real SigLIP weights load and infer locally on CPU; later runs reuse the cache.
- Eight real POI groups ranked the reference photograph first in all eight cases.
- All 247 cached ranking opportunities processed without failures.
- Default actionable research fell from 1,637 tasks to 459 across four cities.
- Jaipur Batch 1 contains 75 tasks; the required-image handoff contains 50.
- Synthetic export/import/rebuild verification passed; no real facts were invented.
- 219 tests passed; dependency checks passed; no live Groq/Gemini calls were made.
- Production source readiness remains blocked by unresolved required photographs.
- Calibration is provisional; measured additional cloud-call savings are zero.

See `reports/local_intelligence/optimization_final.md` for complete evidence and
`docs/local-research-workflow.md` for the workflow. The Jaipur handoff is at
`data/research/exports/jaipur/required_images/research_handoff.json` (or `.md`).

To inspect or recover this state without overwriting subsequent work:

```powershell
git fetch origin --tags
git switch -c codex/recovery-local-ai-research checkpoint/local-ai-research-2026-10-03
```

The local `.env`, virtual environment, model weights, source caches, staging,
scratch directories and test temporary files are intentionally excluded from Git.
On a fresh checkout, install dependencies and prepare the model once:

```powershell
python -m pip install -e '.[dev,local-models]'
python -m datafactory.cli local-ai-status --download
python -m pytest -q --basetemp scratch/checkpoint-verification
```

Configure credentials separately if later cloud assurance is needed. The generated
handoff registry is retained so returned research can be matched strictly against
its registered tasks and source snapshot; a new export is required if that source
snapshot changes.
