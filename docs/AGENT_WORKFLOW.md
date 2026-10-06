# Agent workflow

Last reviewed against repository: 2026-10-06.

## Installed skills and project context

`[IMPLEMENTED]` DataFactory has five local skills in `.agents/skills/`:
`architect`, `imprint`, `recover`, `remember` and `review`.
`skills-lock.json` records the imported source as
`JavaScript-Mastery-Pro/jsm-agent-skill`. This is a different skill pack from the
Flutter projects; do not assume `develop`, `test` or `sync` is installed here.
Project additions are maintained in the existing entrypoints without changing source metadata.

Read [README](../README.md), [local research architecture](local-research-architecture.md),
[local research workflow](local-research-workflow.md), and the configuration or code
relevant to the task. For handoffs, read [offline architecture](OFFLINE_CITY_PACK_ARCHITECTURE.md)
and [the developer loop](CITY_DATA_DEV_LOOP.md).
Historical audits, checkpoints, acceptance reports and session memory are dated
evidence; inspect current code and release heads before treating their paths or counts
as current. This checkout has no root `AGENTS.md` at this review.

## Applying the installed skills

| Skill | DataFactory use and boundary |
| --- | --- |
| `architect` | Resolve pipeline, identity, provenance or export decisions using existing contracts |
| `review` | Review the plan, pipeline boundaries, malformed inputs, media policy and release integrity |
| `recover` | Diagnose a failure and preserve immutable releases, source data and curator work |
| `remember` | Save or restore a short, redacted handoff; memory does not override code or project docs |
| `imprint` | Capture visual patterns when report templates or preview UI actually change |

Generic skill prompts should use decisions and authorization already supplied in the
task. Ask only for unresolved choices that affect the requested outcome. A recovery
recommendation to restart a conversation does not authorize a Git reset or data deletion.
Use `imprint` for visual work; CLI, export and dataset edits do not require a UI registry.

## Immutable data and media policy

`[IMPLEMENTED]` DataFactory owns canonical source records, provenance and versioned
releases. CityPack Lab owns human review and overlays; YatraCanvas consumes a compact
app projection. An authorized repair uses `citylab-import --dry-run` before apply
with a new output version. Review APPLY, REVIEW and REJECT outcomes. Existing release
directories and published IDs remain preserved.

Keep `DRAFT_OFFLINE_READY`, `SOURCE_DATA_READY` and test media classification separate.
Missing factual evidence stays null or unresolved. App fallback presentation does not
establish real-photo coverage, licensing or source readiness. Respect `FREE_ONLY`
configuration and explicit network/model options; an offline check does not authorize
a provider request, model download or paid inference. Keep keys and connection values
out of memory, reports, examples and commits.

Architectural claims use `[IMPLEMENTED]`, `[PARTIAL]`, `[PLANNED]`,
`[DEPRECATED]` or `[UNKNOWN]` and cite repository or test evidence.
`[PARTIAL]` Physical-phone acceptance and measured performance require device evidence.
A successful code review alone does not certify data or prove deployment readiness.

## Verification and publication

Use Python 3.12 or newer and the dependencies in `pyproject.toml`.
Run relevant existing tests with `python -m pytest tests -q`.
For pack export or repair changes, start with `tests/test_citylab_app_pack.py`.
Inspect CLI help before choosing command flags.
Documentation changes need link and diff checks, without rebuilding datasets.

Validate the exact release or projection to be handed off. Pack creation, app asset
sync, GitHub publication and production certification are distinct operations.
Stay within the repositories and actions authorized by the user. Reuse scoped Git
authorization, inspect staged paths, and leave unrelated artifacts out of the commit.
