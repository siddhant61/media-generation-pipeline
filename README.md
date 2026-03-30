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

## Phase 1 Happy Path

The primary Phase 1 workflow reads a structured `ResearchBrief` and produces a contract-valid `ScenePlan`:

```bash
# Generate a ScenePlan from the canonical JWST demo ResearchBrief
python generate_scene_plan.py \
  demo_data/jwst_star_formation_early_universe_demo/ResearchBrief.sample.json \
  --validate

# Also generate a placeholder MediaPackage manifest
python generate_scene_plan.py \
  demo_data/jwst_star_formation_early_universe_demo/ResearchBrief.sample.json \
  --media-package --validate

# Validate any artifact against the shared contract
python validate_artifacts.py generated_artifacts/
```

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
├── demo_data/                  # Canonical demo scaffold
│   └── jwst_star_formation_early_universe_demo/
│       ├── ResearchBrief.sample.json   # Populated JWST research brief
│       ├── ScenePlan.sample.json       # Reference scene plan
│       ├── RunManifest.sample.json     # Reference run manifest
│       └── manifest.json               # RawSourceBundle
│
│── Phase 1 modules (structured input → artifact output)
├── scene_plan_generator.py     # ResearchBrief → ScenePlan (core Phase 1)
├── media_package_writer.py     # ScenePlan → placeholder MediaPackage
├── run_manifest_writer.py      # RunManifest generation
├── generate_scene_plan.py      # CLI entrypoint for Phase 1 happy path
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
├── tests/                      # Test suite
│   ├── test_scene_plan_generator.py  # Phase 1 happy path tests (41 tests)
│   ├── test_bridge.py          # Phase 1.5 bridge tests (25 tests)
│   ├── test_pipeline.py        # Legacy pipeline tests
│   ├── test_api.py             # API endpoint tests
│   ├── test_api_security.py    # Security tests
│   └── test_job_store.py       # Redis job store tests
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
# Run all tests (115 tests)
pytest tests/ -v

# Run Phase 1 happy path tests only
pytest tests/test_scene_plan_generator.py -v

# Run Phase 1.5 bridge tests only
pytest tests/test_bridge.py -v

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

## Phase 1 Blockers & Status

| Item | Status | Notes |
|---|---|---|
| ScenePlan generation from ResearchBrief | ✅ Working | Deterministic, no API keys needed |
| Artifact validation against contract | ✅ Working | All 3 artifact types validated |
| Placeholder MediaPackage | ✅ Working | Lists expected assets without rendering |
| Bridge: ScenePlan → legacy Scene mapping | ✅ Working | `bridge_adapter.py` maps all fields correctly |
| Bridge CLI (structured input path) | ✅ Working | Accepts ResearchBrief or ScenePlan, emits all artifacts |
| Bridged MediaPackage with render metadata | ✅ Working | Records exactly where rendering was blocked |
| Full video rendering from ScenePlan | ⚠️ API-gated | Requires `OPENAI_API_KEY` + `STABILITY_API_KEY`; pipeline stops at `content_generator_init` without them |
| LLM-enhanced scene generation | ⚠️ Future | Could enhance scene narration/visuals via LLM |

## 📄 License

MIT License. See [LICENSE](LICENSE) for details. 