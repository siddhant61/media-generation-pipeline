# Audit Package — media-generation-pipeline

> Audit date: 2026-03-30  
> Auditor: automated  
> Commit baseline: all 90 tests passing, Phase 1 happy path verified  

---

## 1. Current Entrypoints

| File | Type | Invocation | Status |
|---|---|---|---|
| `generate_scene_plan.py` | CLI (argparse) | `python generate_scene_plan.py <ResearchBrief.json> [--media-package] [--validate]` | ✅ Working — no API keys needed |
| `validate_artifacts.py` | CLI (argparse) | `python validate_artifacts.py <artifact.json \| dir/>` | ✅ Working — validates against `contracts/shared_artifacts.json` |
| `cli.py` | CLI (argparse) | `python cli.py "Topic" [--num-scenes N] [--static-scenes]` | ⚠️ Requires `OPENAI_API_KEY` + `STABILITY_API_KEY` |
| `main.py` | FastAPI app | `uvicorn main:app --port 8000` | ⚠️ Requires API keys at runtime |
| `setup.py` console_scripts | Package entrypoints | `media-pipeline` → `cli:main`, `media-pipeline-api` → `main:main` | ⚠️ Only legacy modules registered |

**Note:** Phase 1 modules (`scene_plan_generator`, `media_package_writer`, `run_manifest_writer`, `generate_scene_plan`, `validate_artifacts`) are **not listed** in `setup.py` `py_modules` and have **no console_script** entries.

---

## 2. Repo Purpose as Implemented Today

The repository serves **two distinct purposes** that coexist but are not yet integrated:

### Phase 1 (structured artifact pipeline) — WORKING
- Reads a contract-valid `ResearchBrief` (from `content-research-pipeline`)
- Produces a contract-valid `ScenePlan` via deterministic template logic
- Optionally produces a placeholder `MediaPackage` manifest (no actual rendering)
- Emits a `RunManifest` tracking the pipeline run
- All outputs validated against `contracts/shared_artifacts.json`
- **No API keys required. No external calls. Fully reproducible.**

### Legacy pipeline (topic → video via API) — FUNCTIONAL BUT ISOLATED
- Accepts a free-form topic string
- Generates scenes via OpenAI LLM → images via Stability AI → audio via OpenAI TTS → video via MoviePy
- Exposes a FastAPI REST API with job tracking (Redis or in-memory)
- Has a web UI for browser-based generation
- **Requires API keys. Not integrated with shared contracts.**

The two paths share no runtime code — `scene_plan_generator.py` and `scene_manager.py` define completely different scene representations.

---

## 3. Mismatch vs README

The README (updated in the prior PR) is **largely accurate**. Specific issues:

| Claim in README | Actual state | Severity |
|---|---|---|
| "90 tests" | ✅ Confirmed: 90 tests, all passing | None |
| Phase 1 happy path commands | ✅ All work as documented | None |
| "Legacy pipeline … not yet integrated with structured artifact workflow" | ✅ Accurate | None |
| Project structure listing | ✅ Matches actual file layout | None |
| `setup.py` section absent | `setup.py` does not list Phase 1 modules in `py_modules` | Low — cosmetic but could affect `pip install -e .` discoverability |
| No mention of `.gitignore` suppressing `*.json` | `.gitignore` contains `*.json` globally, which could prevent new demo JSON from being tracked unless force-added | Low |

**Verdict:** README is accurate. Minor gap: no mention of `setup.py` Phase 1 gap.

---

## 4. Mismatch vs contracts/shared_artifacts.json and contracts/schemas.md

### 4a. Artifacts this repo should own

Per `shared_artifacts.json`:
- **ScenePlan** — `owned_by: ["media-generation-pipeline"]` ✅
- **MediaPackage** — `owned_by: ["media-generation-pipeline"]` ✅
- **RunManifest** — `owned_by: [all three repos]` ✅

### 4b. Artifacts this repo should consume

- **ResearchBrief** — `consumed_by: ["media-generation-pipeline"]` ✅
- **KnowledgeGraphPackage** — `consumed_by: ["content-research-pipeline", "media-generation-pipeline"]` — **Not consumed yet** (Phase 2 concern)

### 4c. Schema compliance

| Artifact | Phase 1 module | Contract-compliant? | Notes |
|---|---|---|---|
| ScenePlan | `scene_plan_generator.py` | ✅ All 11 top-level + 10 scene fields present | Validated by tests and runtime |
| MediaPackage | `media_package_writer.py` | ✅ All 11 top-level + 9 asset fields present | Placeholder only — assets not rendered |
| RunManifest | `run_manifest_writer.py` | ✅ All 13 required fields present | |
| ResearchBrief | `scene_plan_generator.load_research_brief()` | ✅ All 16 required fields checked | Consumer validation |

### 4d. Legacy scene format mismatch

The legacy `Scene` dataclass in `scene_manager.py` uses fields `{id, name, prompt, narration, image_file, audio_file}`. The contract requires `{scene_id, title, purpose, narration, visual_brief, on_screen_text, entity_refs, citation_refs, duration_seconds, transition}`. These share only `narration` — **the legacy scene format is not contract-compliant**.

### 4e. Filename pattern

Contract specifies `<topic_slug>__<artifact_type>__<timestamp>.json`. Phase 1 `generate_scene_plan.py` follows this convention. ✅

**Verdict:** Phase 1 modules are fully contract-compliant. Legacy pipeline is entirely non-compliant at the scene level. The bridge between them is the highest-leverage future work.

---

## 5. Happy-Path Status

### Phase 1 happy path: ✅ STABLE

```
ResearchBrief.sample.json
    ↓  (scene_plan_generator.py)
ScenePlan  ← contract-valid, 7 scenes from JWST demo
    ↓  (media_package_writer.py)
MediaPackage  ← placeholder manifest, no rendered assets
    ↓  (run_manifest_writer.py)
RunManifest  ← pipeline run tracking
```

Verified via:
- `python generate_scene_plan.py demo_data/jwst_star_formation_early_universe_demo/ResearchBrief.sample.json --media-package --validate` → all outputs VALID
- `python -m pytest tests/test_scene_plan_generator.py -v` → 41/41 pass
- `python validate_artifacts.py demo_data/jwst_star_formation_early_universe_demo/` → all sample artifacts VALID

### Legacy video pipeline: ⚠️ FUNCTIONAL BUT API-GATED

Tested via mocked tests (all pass), but actual execution requires:
1. `OPENAI_API_KEY` (for LLM scene gen + TTS)
2. `STABILITY_API_KEY` (for image gen)
3. Redis (optional, for job persistence)

---

## 6. Broken or Fragile Paths

| Path | Issue | Severity |
|---|---|---|
| Legacy pipeline → ScenePlan | Legacy `Scene` dataclass is not contract-compliant. No bridge exists. | **Medium** — blocks eventual full rendering from contract data |
| `setup.py` `py_modules` | Phase 1 modules (`scene_plan_generator`, etc.) not listed. `pip install -e .` installs them only because they're in the root dir, but `pip install media-generation-pipeline` from sdist/wheel would miss them. | **Low** — works in dev, would fail in wheel distribution |
| `.gitignore` global `*.json` | New JSON files added to repo root or subdirs would be ignored by git. Demo JSON files are tracked only because they were force-added. | **Low** — footgun for future contributors |
| `main.py` uses `datetime.utcnow()` | Deprecated in Python 3.12+; emits deprecation warnings in tests | **Low** — cosmetic, not breaking |
| `main.py` uses `@app.on_event("startup")` | Deprecated in current FastAPI; emits deprecation warnings | **Low** — cosmetic, not breaking |

No paths are **broken**. The only **fragile** area is the unstated assumption that the two scene representations (legacy `Scene` vs contract scenes) are separate systems.

---

## 7. Highest-Leverage Phase 1 Changes

Prioritized by impact-to-effort ratio:

| # | Change | Impact | Effort | Why |
|---|---|---|---|---|
| 1 | **Register Phase 1 modules in `setup.py`** | Correct packaging | Trivial | 5 modules missing from `py_modules`; no console_script for Phase 1 CLI |
| 2 | **Bridge ScenePlan → legacy renderer** | Unlocks full video from structured input | Medium | Adapter function: contract `ScenePlan.scenes[]` → legacy `Scene` dataclass |
| 3 | **Add `--research-brief` mode to `cli.py`** | Unified entry point | Small | Let `cli.py` accept a `ResearchBrief` path instead of only a topic string |
| 4 | **Wire ScenePlan into FastAPI `/generate`** | API consumers can use structured input | Medium | Accept `research_brief` field in `GenerateRequest` |
| 5 | **Add KnowledgeGraphPackage consumption** | Richer scene content | Large | Phase 2 — not needed for happy path |

**Recommendation for Phase 1 implementation sprint:**
- Items 1 is a trivial fix (this PR).
- Items 2–4 form the "bridge" work that connects the two systems.
- Item 5 is Phase 2.

---

## 8. Proposed Implementation Order

### Phase 1a — This PR (audit + minimal scaffolding)
1. ✅ Create this `AUDIT.md`
2. Fix `setup.py` `py_modules` to include Phase 1 modules
3. No broad implementation changes

### Phase 1b — Bridge PR (next sprint)
1. Create `scene_plan_adapter.py`: `contract_scene_to_legacy(scene_dict) → Scene`
2. Add `--research-brief <path>` to `cli.py` 
3. Wire `ResearchBrief` path into `main.py` `/generate` endpoint
4. Add integration tests for the bridge

### Phase 1c — Rendering validation
1. Test full render with API keys: `ResearchBrief → ScenePlan → Scene → image+audio → video`
2. Update `MediaPackage` from placeholder to rendered on success
3. Update `RunManifest` with rendering metrics

### Phase 2 — Enrich
1. Consume `KnowledgeGraphPackage` for richer entity context
2. LLM-enhanced narration/visual briefs
3. Multi-format output (vertical video, social clips)

---

## 9. Validation Plan

| Check | Command | Expected |
|---|---|---|
| All tests pass | `python -m pytest tests/ -v` | 90/90 pass |
| Phase 1 happy path | `python generate_scene_plan.py demo_data/…/ResearchBrief.sample.json --media-package --validate` | 3 valid artifacts |
| Artifact contract validation | `python validate_artifacts.py <any_artifact.json>` | VALID for conforming files |
| Demo samples valid | `python validate_artifacts.py demo_data/jwst_star_formation_early_universe_demo/` | All 3 sample files VALID |
| Package installable | `pip install -e . && python -c "import scene_plan_generator"` | No import error |

All checks verified during this audit.

---

## 10. Cross-Repo Implications

### For `content-research-pipeline`
- **No changes needed.** This repo correctly consumes the `ResearchBrief` format as defined in the shared contract.
- The `ResearchBrief.sample.json` in demo_data serves as a testable interface contract.

### For `material-ingestion-pipeline`
- **No direct dependency.** This repo does not consume `RawSourceBundle`, `NormalizedDocumentSet`, `ChunkSet`, or `KnowledgeGraphPackage` in Phase 1.
- `KnowledgeGraphPackage` consumption is a Phase 2 item.

### Contract tensions
- **None found.** The `contracts/shared_artifacts.json` is consistent across all three repos. The Phase 1 modules in this repo strictly follow the contract.
- The **legacy pipeline** does not follow the contract but is documented as separate.

### Filename convention
- Contract: `<topic_slug>__<artifact_type>__<timestamp>.json`
- Phase 1 implementation: follows this convention ✅
- Legacy pipeline: outputs to `generated_content/` with different naming — **non-compliant but isolated**

---

## Summary

| Area | Status |
|---|---|
| Phase 1 happy path | ✅ Stable and contract-valid |
| Test suite | ✅ 90/90 passing |
| Contract compliance | ✅ Phase 1 modules fully compliant |
| Legacy pipeline | ⚠️ Functional but isolated from contracts |
| README accuracy | ✅ Accurate |
| Packaging | ⚠️ Phase 1 modules missing from setup.py |
| Blockers for full rendering | API keys + bridge adapter needed |
