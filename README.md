# Media Generation Pipeline

The downstream generation and showcase module of a 3-part AI workflow stack. This repository consumes structured research artifacts (produced by `content-research-pipeline`) and generates scene plans, media packages, and video content.

## System Context

This repo is part of a coordinated multi-repo system:

| Repository | Role |
|---|---|
| `material-ingestion-pipeline` | Ingests raw sources → produces NormalizedDocumentSet, ChunkSet, KnowledgeGraphPackage |
| `content-research-pipeline` | Researches topics → produces **ResearchBrief** |
| **`media-generation-pipeline`** | **Consumes ResearchBrief → produces ScenePlan, MediaPackage, RunManifest** |

Shared contracts are defined in [`contracts/shared_artifacts.json`](contracts/shared_artifacts.json) and [`contracts/schemas.md`](contracts/schemas.md).

## Phase 1 / Phase 2B Happy Path

The primary workflow reads a structured `ResearchBrief` and produces a contract-valid `ScenePlan`, placeholder `MediaPackage`, and `RunManifest`. In Phase 2B the input can be a bare JSON file or a **handoff directory** (the format `content-research-pipeline` writes), and outputs can be written to a **stable location** (`outputs/<topic_slug>/`).

```bash
# Generate a ScenePlan from the canonical JWST demo ResearchBrief (file)
python generate_scene_plan.py \
  demo_data/jwst_star_formation_early_universe_demo/ResearchBrief.sample.json \
  --validate

# Also generate a placeholder MediaPackage manifest
python generate_scene_plan.py \
  demo_data/jwst_star_formation_early_universe_demo/ResearchBrief.sample.json \
  --media-package --validate

# Use a canonical fixture from content-research-pipeline
python generate_scene_plan.py \
  fixtures/research_briefs/jwst_canonical.json \
  --media-package --validate

# Phase 2B: load from a handoff directory + write to stable output location
python generate_scene_plan.py \
  demo_data/jwst_star_formation_early_universe_demo/ \
  --media-package --stable-output --validate

# Validate any artifact against the shared contract
python validate_artifacts.py generated_artifacts/

# Validate stable canonical outputs
python validate_artifacts.py outputs/jwst_star_formation_early_universe_demo/
```

### Canonical ResearchBrief Fixtures

The `fixtures/research_briefs/` directory provides stable input fixtures that simulate artifacts produced by `content-research-pipeline`. These are used for integration testing and as the primary input path for downstream handoff validation.

```python
from scene_plan_generator import load_research_brief_fixture, list_research_brief_fixtures

# List available fixtures
print(list_research_brief_fixtures())  # ['jwst_canonical']

# Load a fixture and generate a ScenePlan
brief = load_research_brief_fixture("jwst_canonical")
plan = generate_scene_plan(brief)
```

The provenance chain from upstream research is preserved:

```
ResearchBrief.source_index[].source_id
    → ResearchBrief.key_findings[].citation_refs[]
    → ScenePlan.scenes[].citation_refs[]
```

## Phase 2B Happy Path: Canonical ResearchBrief Handoff

Phase 2B adds a dedicated **handoff loader** that consumes the canonical
`ResearchBrief` artifact emitted by `content-research-pipeline` — whether
delivered as a bare JSON file or as a structured handoff directory — and
writes all outputs to a **stable, documented location**.

### Upstream input expected

| Input | Location | Description |
|---|---|---|
| `ResearchBrief` JSON file | `fixtures/research_briefs/jwst_canonical.json` | Canonical fixture (simulates content-research-pipeline output) |
| Handoff directory | `demo_data/jwst_star_formation_early_universe_demo/` | Directory with ResearchBrief + sibling artifacts |

The `ResearchBrief` must have `"producer": "content-research-pipeline"` and
satisfy all `required_fields` defined in `contracts/shared_artifacts.json`.

### Canonical outputs produced

| Artifact | Stable path | Description |
|---|---|---|
| `ScenePlan` | `outputs/<topic_slug>/ScenePlan.json` | Contract-valid scene plan from research brief |
| `MediaPackage` | `outputs/<topic_slug>/MediaPackage.json` | Placeholder MediaPackage listing expected assets |
| `RunManifest` | `outputs/<topic_slug>/RunManifest.json` | Pipeline run tracking artifact |

The JWST demo stable outputs live at:

```
outputs/jwst_star_formation_early_universe_demo/
├── ScenePlan.json
├── MediaPackage.json
└── RunManifest.json
```

### Phase 2B happy path commands

```bash
# Load from a bare ResearchBrief file + write to stable output
python generate_scene_plan.py \
  fixtures/research_briefs/jwst_canonical.json \
  --media-package --stable-output --validate

# Load from a handoff directory (auto-detects ResearchBrief)
python generate_scene_plan.py \
  demo_data/jwst_star_formation_early_universe_demo/ \
  --media-package --stable-output --validate

# Validate the stable canonical outputs
python validate_artifacts.py outputs/jwst_star_formation_early_universe_demo/
```

### Handoff loader API

```python
from research_brief_handoff import (
    load_handoff_package,
    emit_stable_outputs,
    list_stable_outputs,
)
from scene_plan_generator import generate_scene_plan
from media_package_writer import create_media_package
from run_manifest_writer import create_run_manifest

# Load from a file or a handoff directory
brief, meta = load_handoff_package("fixtures/research_briefs/jwst_canonical.json")
brief, meta = load_handoff_package("demo_data/jwst_star_formation_early_universe_demo/")

# Generate canonical artifacts
plan = generate_scene_plan(brief)
pkg  = create_media_package(plan, rendered=False)
manifest = create_run_manifest(
    pipeline_stage="scene_plan_generation",
    status="complete",
    inputs={"research_brief": meta["brief_path"]},
    outputs=[],
    metrics={"num_scenes": len(plan["scenes"])},
    source_run_id=plan["source_run_id"],
)

# Write to stable output location (outputs/<topic_slug>/)
paths = emit_stable_outputs(plan, pkg, manifest)
# → {"ScenePlan": "outputs/.../ScenePlan.json", ...}

# Check what stable outputs exist
found = list_stable_outputs("jwst_star_formation_early_universe_demo")
```

### Provenance chain (Phase 2B)

Citation and entity references are preserved end-to-end through the handoff:

```
ResearchBrief.source_index[].source_id          # canonical source IDs from content-research-pipeline
    → ResearchBrief.key_findings[].citation_refs[] # per-finding citations
    → ScenePlan.scenes[].citation_refs[]            # carried into each scene

ResearchBrief.entities[].label                   # entity labels
    → ScenePlan.scenes[].entity_refs[]              # carried into each scene
```

### What remains API-gated

Full rendering (images, audio, video assembly) requires API keys. Without them
the pipeline emits a **placeholder MediaPackage** documenting the expected
assets without actual files.

| Path | Status |
|---|---|
| `ResearchBrief` → `ScenePlan` | ✅ No API keys needed |
| `ScenePlan` → placeholder `MediaPackage` | ✅ No API keys needed |
| `ScenePlan` → rendered images | ⚠️ Requires `STABILITY_API_KEY` |
| `ScenePlan` → TTS audio | ⚠️ Requires `OPENAI_API_KEY` |
| `ScenePlan` → assembled video | ⚠️ Requires both keys above |

## Phase 1.5 Bridge: ScenePlan → Legacy Rendering

The bridge adapter (`bridge_adapter.py`) connects the contract-aligned ScenePlan to the legacy rendering pipeline (SceneManager → ContentGenerator → VideoAssembler). The bridge CLI (`bridge_cli.py`) provides a single entry point that:

1. Accepts a **ResearchBrief** or **ScenePlan** as input
2. Generates a ScenePlan (if starting from ResearchBrief)
3. Bridges contract scenes to legacy `Scene` dataclass instances
4. Optionally attempts full rendering through the legacy pipeline
5. Emits a contract-valid **MediaPackage** with rich bridge/render metadata

```bash
# Dry-run: bridge + validate (no API keys needed)
python bridge_cli.py \
  demo_data/jwst_star_formation_early_universe_demo/ResearchBrief.sample.json \
  --dry-run --validate

# Using canonical fixture from content-research-pipeline
python bridge_cli.py \
  fixtures/research_briefs/jwst_canonical.json \
  --dry-run --validate

# From an existing ScenePlan
python bridge_cli.py \
  demo_data/jwst_star_formation_early_universe_demo/ScenePlan.sample.json \
  --scene-plan --dry-run --validate

# Full render attempt (requires OPENAI_API_KEY + STABILITY_API_KEY)
python bridge_cli.py \
  demo_data/jwst_star_formation_early_universe_demo/ResearchBrief.sample.json \
  --render --validate
```

### Bridge field mapping

| Contract ScenePlan scene field | Legacy Scene field |
|---|---|
| `scene_id` | `id` |
| `title` | `name` |
| `visual_brief` | `prompt` |
| `narration` | `narration` |
| _(not yet rendered)_ | `image_file` = `""` |
| _(not yet rendered)_ | `audio_file` = `""` |

### What requires API keys

The bridge itself (ScenePlan → legacy Scene mapping) requires **no API keys**. Full rendering requires:

| Service | Env Variable | Used For |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | LLM narration generation + TTS audio |
| Stability AI | `STABILITY_API_KEY` | Image generation |

Without these keys, rendering stops at the `content_generator_init` stage and a placeholder MediaPackage is emitted with metadata documenting exactly where rendering was blocked.

### Minimum renderable happy path

1. Set `OPENAI_API_KEY` and `STABILITY_API_KEY` environment variables
2. Run `python bridge_cli.py <ResearchBrief.json> --render --validate`
3. Pipeline will: generate ScenePlan → bridge scenes → generate images/audio via APIs → assemble video via MoviePy

### What gets produced

| Artifact | Status | Description |
|---|---|---|
| `ScenePlan` | ✅ Stable | Scene-by-scene plan built from ResearchBrief findings, timeline, entities |
| `RunManifest` | ✅ Stable | Pipeline run tracking with inputs, outputs, metrics |
| `MediaPackage` | ✅ Bridged | Contract-valid manifest with bridge render metadata; placeholder assets when rendering is API-gated |

All outputs follow the naming convention: `<topic_slug>__<artifact_type>__<timestamp>.json`

### Canonical demo

The `demo_data/jwst_star_formation_early_universe_demo/` directory contains:

- `ResearchBrief.sample.json` — Populated JWST research brief (input)
- `ScenePlan.sample.json` — Example scene plan (reference output)
- `RunManifest.sample.json` — Example run manifest
- `manifest.json` — RawSourceBundle listing NASA/ESA sources

## 📁 Project Structure

```
media-generation-pipeline/
├── contracts/                  # Shared artifact contracts (source of truth)
│   ├── shared_artifacts.json   # JSON schema definitions for all artifacts
│   ├── schemas.md              # Markdown schema documentation
│   └── demo_manifest.md        # Demo configuration and happy path steps
├── fixtures/                   # Canonical input fixtures
│   └── research_briefs/        # ResearchBrief fixtures from content-research-pipeline
│       └── jwst_canonical.json # Canonical JWST demo fixture
├── demo_data/                  # Canonical demo scaffold (handoff directory example)
│   └── jwst_star_formation_early_universe_demo/
│       ├── ResearchBrief.sample.json   # Populated JWST research brief (upstream handoff)
│       ├── ScenePlan.sample.json       # Reference scene plan
│       ├── RunManifest.sample.json     # Reference run manifest
│       └── manifest.json               # RawSourceBundle
├── outputs/                    # Stable canonical outputs (per-topic, no timestamps)
│   └── jwst_star_formation_early_universe_demo/
│       ├── ScenePlan.json      # Canonical ScenePlan output
│       ├── MediaPackage.json   # Canonical placeholder MediaPackage output
│       └── RunManifest.json    # Canonical RunManifest output
│
│── Phase 1 / Phase 2B modules (structured input → artifact output)
├── scene_plan_generator.py     # ResearchBrief → ScenePlan (core Phase 1)
├── research_brief_handoff.py   # Phase 2B: handoff loader + stable output emitter
├── media_package_writer.py     # ScenePlan → placeholder MediaPackage
├── run_manifest_writer.py      # RunManifest generation
├── generate_scene_plan.py      # CLI: file or handoff dir → ScenePlan (+ --stable-output)
├── validate_artifacts.py       # Validate artifacts against shared contract
│
│── Phase 1.5 bridge (ScenePlan → legacy rendering pipeline)
├── bridge_adapter.py           # ScenePlan scenes → legacy Scene dataclass
├── bridge_cli.py               # CLI: ResearchBrief/ScenePlan → bridge → render → MediaPackage
│
│── Legacy pipeline modules (topic → video via API calls)
├── config.py                   # Configuration (LLM, TTS, Video, API settings)
├── scene_manager.py            # Dynamic and static scene management
├── content_generator.py        # OpenAI (LLM, TTS) and Stability AI integration
├── image_processor.py          # Image processing and visualization
├── video_assembler.py          # MP4 video creation with MoviePy
├── cli.py                      # Legacy CLI (topic → video)
├── main.py                     # FastAPI server for REST API
│
├── services/                   # Production services
│   └── job_store.py            # Redis-based job persistence
├── ui/                         # Web UI for video generation
├── tests/                      # Test suite (196 tests)
│   ├── test_scene_plan_generator.py       # Phase 1 happy path tests (41 tests)
│   ├── test_bridge.py                     # Phase 1.5 bridge tests (25 tests)
│   ├── test_research_brief_handoff.py     # Phase 2A fixture handoff tests (36 tests)
│   ├── test_phase2b_integration.py        # Phase 2B integration tests (45 tests)
│   ├── test_pipeline.py                   # Legacy pipeline tests
│   ├── test_api.py                        # API endpoint tests
│   ├── test_api_security.py               # Security tests
│   └── test_job_store.py                  # Redis job store tests
├── setup.py                    # Package setup
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Multi-stage Docker build
└── docker-compose.yml          # Docker Compose (API + Redis)
```

## 🛠️ Installation

```bash
git clone https://github.com/siddhant61/media-generation-pipeline.git
cd media-generation-pipeline
pip install -e .
```

## 🧪 Testing

```bash
# Run all tests (196 tests)
pytest tests/ -v

# Run Phase 1 happy path tests only
pytest tests/test_scene_plan_generator.py -v

# Run Phase 1.5 bridge tests only
pytest tests/test_bridge.py -v

# Run Phase 2A fixture handoff tests only
pytest tests/test_research_brief_handoff.py -v

# Run Phase 2B integration tests only
pytest tests/test_phase2b_integration.py -v

# Run legacy pipeline tests
pytest tests/test_pipeline.py tests/test_api.py -v
```

## Validation

```bash
# Validate generated artifacts against the shared contract
python validate_artifacts.py generated_artifacts/

# Validate a single artifact
python validate_artifacts.py demo_data/jwst_star_formation_early_universe_demo/ScenePlan.sample.json

# Run the full happy path with validation
python generate_scene_plan.py \
  demo_data/jwst_star_formation_early_universe_demo/ResearchBrief.sample.json \
  --media-package --validate
```

## Legacy Pipeline (Full Rendering)

The legacy pipeline generates full video content from a topic string using external APIs. This requires API keys and is not yet integrated with the structured artifact workflow.

### CLI Mode
```bash
export OPENAI_API_KEY='your-key'
export STABILITY_API_KEY='your-key'
python cli.py "The History of Space Exploration"
```

### API Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "The Solar System", "num_scenes": 8}'
```

### Docker Mode
```bash
cp .env.example .env   # Add your API keys
docker-compose up -d
```

See [API.md](API.md) for full REST API documentation and [DEPLOYMENT.md](DEPLOYMENT.md) for deployment guides.

## Minimum Renderable Path

The following describes the minimum path that works without external API keys, and what requires API keys.

### Works without API keys (always available)

1. **Load a ResearchBrief** — from `fixtures/research_briefs/`, `demo_data/`, or any valid JSON
2. **Generate a ScenePlan** — deterministic scene generation from structured brief data
3. **Validate all artifacts** — check against `contracts/shared_artifacts.json`
4. **Bridge to legacy scenes** — map contract ScenePlan → legacy Scene dataclass
5. **Emit placeholder MediaPackage** — contract-valid manifest listing expected assets

```bash
python bridge_cli.py fixtures/research_briefs/jwst_canonical.json --dry-run --validate
```

### Requires API keys (rendering path)

Full rendering through the legacy pipeline requires external API keys. Without them, the pipeline stops at the `content_generator_init` stage and emits a placeholder MediaPackage documenting the block.

| Stage | Requires | Description |
|---|---|---|
| `content_generator_init` | `OPENAI_API_KEY` | Initialize LLM/TTS content generator |
| `content_generation` | `OPENAI_API_KEY` | Generate scene narration/text via LLM |
| `audio_generation` | `OPENAI_API_KEY` | Generate TTS audio for narration |
| `content_generation` (images) | `STABILITY_API_KEY` | Generate scene images via Stability AI |
| `video_assembly` | _(none — uses MoviePy)_ | Assemble final video from images + audio |

```bash
export OPENAI_API_KEY='your-key'
export STABILITY_API_KEY='your-key'
python bridge_cli.py fixtures/research_briefs/jwst_canonical.json --render --validate
```

## Phase Status

| Item | Status | Notes |
|---|---|---|
| ScenePlan generation from ResearchBrief | ✅ Working | Deterministic, no API keys needed |
| Canonical fixture input path | ✅ Working | `fixtures/research_briefs/` with JWST canonical fixture |
| Citation/provenance preservation | ✅ Working | `citation_refs` flow from findings → scenes; validated by tests |
| Artifact validation against contract | ✅ Working | All 3 artifact types validated |
| Placeholder MediaPackage | ✅ Working | Lists expected assets without rendering |
| Bridge: ScenePlan → legacy Scene mapping | ✅ Working | `bridge_adapter.py` maps all fields correctly |
| Bridge CLI (structured input path) | ✅ Working | Accepts ResearchBrief or ScenePlan, emits all artifacts |
| Bridged MediaPackage with render metadata | ✅ Working | Records exactly where rendering was blocked |
| Fixture-based integration tests | ✅ Working | 36 tests covering handoff, provenance, CLI pipeline |
| **Handoff package loader** | ✅ Working (Phase 2B) | `research_brief_handoff.py` — file or directory input |
| **Stable output location** | ✅ Working (Phase 2B) | `outputs/<topic_slug>/` with fixed filenames |
| **Phase 2B integration tests** | ✅ Working (Phase 2B) | 45 tests covering handoff, stable output, end-to-end |
| **CLI directory input** | ✅ Working (Phase 2B) | `generate_scene_plan.py <directory> --stable-output` |
| Full video rendering from ScenePlan | ⚠️ API-gated | Requires `OPENAI_API_KEY` + `STABILITY_API_KEY`; pipeline stops at `content_generator_init` without them |
| LLM-enhanced scene generation | ⚠️ Future | Could enhance scene narration/visuals via LLM |

## 📄 License

MIT License. See [LICENSE](LICENSE) for details. 