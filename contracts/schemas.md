# Shared Artifact Schemas
Version: 1.0.0

This file defines the shared artifact contract across:

- material-ingestion-pipeline
- content-research-pipeline
- media-generation-pipeline

The goal is to keep all three repositories interoperable through stable, explicit,
versioned artifacts.

## Design Principles

1. Every artifact must include:
   - `artifact_type`
   - `schema_version`
   - `artifact_id`
   - `created_at`
   - `producer`
   - `source_run_id`

2. Artifacts should be:
   - serializable to JSON
   - human-inspectable
   - append-only where practical
   - easy to validate

3. Cross-repo compatibility is more important than local elegance.

4. New fields may be added in a backward-compatible way.
   Existing required fields must not be removed without a schema version bump.

## Canonical Artifact Flow

`RawSourceBundle -> NormalizedDocumentSet -> ChunkSet -> KnowledgeGraphPackage -> ResearchBrief -> ScenePlan -> MediaPackage`

Supporting artifact: `RunManifest`

## Artifact: RunManifest

Required fields:
- `artifact_type`: `"RunManifest"`
- `schema_version`
- `artifact_id`
- `created_at`
- `producer`
- `source_run_id`
- `pipeline_name`
- `pipeline_stage`
- `status`
- `inputs`
- `outputs`
- `metrics`
- `errors`

## Artifact: RawSourceBundle

Represents the canonical list of raw source inputs for a topic/demo.

Required fields:
- `artifact_type`: `"RawSourceBundle"`
- `schema_version`
- `artifact_id`
- `created_at`
- `producer`
- `source_run_id`
- `topic`
- `source_bundle_name`
- `sources`

Each `sources[]` item:
- `source_id`
- `title`
- `source_type`
- `origin_org`
- `url`
- `local_path`
- `mime_type`
- `language`
- `license`
- `usage_notes`
- `retrieved_at`
- `checksum`
- `tags`

## Artifact: NormalizedDocumentSet

Required fields:
- `artifact_type`: `"NormalizedDocumentSet"`
- `schema_version`
- `artifact_id`
- `created_at`
- `producer`
- `source_run_id`
- `topic`
- `documents`

Each `documents[]` item:
- `document_id`
- `source_id`
- `title`
- `document_type`
- `language`
- `text`
- `sections`
- `metadata`

Each `sections[]` item:
- `section_id`
- `heading`
- `text`
- `order_index`
- `page_start`
- `page_end`
- `time_start`
- `time_end`

## Artifact: ChunkSet

Required fields:
- `artifact_type`: `"ChunkSet"`
- `schema_version`
- `artifact_id`
- `created_at`
- `producer`
- `source_run_id`
- `topic`
- `chunking_strategy`
- `chunks`

Each `chunks[]` item:
- `chunk_id`
- `document_id`
- `source_id`
- `text`
- `token_count`
- `char_count`
- `embedding_model`
- `embedding_vector_ref`
- `metadata`

Metadata may include:
- `section_id`
- `page`
- `time_start`
- `time_end`
- `speaker`
- `modality`
- `keywords`

## Artifact: KnowledgeGraphPackage

Required fields:
- `artifact_type`: `"KnowledgeGraphPackage"`
- `schema_version`
- `artifact_id`
- `created_at`
- `producer`
- `source_run_id`
- `topic`
- `graph_name`
- `nodes`
- `edges`
- `embeddings_index`
- `provenance`

Each `nodes[]` item:
- `node_id`
- `label`
- `node_type`
- `description`
- `aliases`
- `attributes`
- `source_refs`

Each `edges[]` item:
- `edge_id`
- `source_node_id`
- `target_node_id`
- `relation_type`
- `weight`
- `evidence`
- `source_refs`

Each `source_refs[]` item:
- `source_id`
- `document_id`
- `chunk_id`
- `quote`
- `confidence`

## Artifact: ResearchBrief

Required fields:
- `artifact_type`: `"ResearchBrief"`
- `schema_version`
- `artifact_id`
- `created_at`
- `producer`
- `source_run_id`
- `topic`
- `research_question`
- `executive_summary`
- `key_findings`
- `entities`
- `timeline`
- `source_index`
- `citation_map`
- `open_questions`
- `recommended_angles`

Each `key_findings[]` item:
- `finding_id`
- `claim`
- `importance`
- `confidence`
- `evidence_refs`

Each `source_index[]` item:
- `source_id`
- `title`
- `origin_org`
- `url`
- `source_type`
- `credibility_notes`

## Artifact: ScenePlan

Required fields:
- `artifact_type`: `"ScenePlan"`
- `schema_version`
- `artifact_id`
- `created_at`
- `producer`
- `source_run_id`
- `topic`
- `narrative_goal`
- `target_audience`
- `style_profile`
- `scenes`

Each `scenes[]` item:
- `scene_id`
- `title`
- `purpose`
- `narration`
- `visual_brief`
- `on_screen_text`
- `entity_refs`
- `citation_refs`
- `duration_seconds`
- `transition`

## Artifact: MediaPackage

Required fields:
- `artifact_type`: `"MediaPackage"`
- `schema_version`
- `artifact_id`
- `created_at`
- `producer`
- `source_run_id`
- `topic`
- `media_type`
- `assets`
- `render_manifest`
- `attribution`

Each `assets[]` item:
- `asset_id`
- `asset_type`
- `title`
- `local_path`
- `mime_type`
- `duration_seconds`
- `resolution`
- `source_scene_id`
- `metadata`

## Repo Ownership

### material-ingestion-pipeline owns
- `RawSourceBundle`
- `NormalizedDocumentSet`
- `ChunkSet`
- `KnowledgeGraphPackage`
- `RunManifest` for ingestion runs

### content-research-pipeline owns
- `ResearchBrief`
- optional enriched `KnowledgeGraphPackage`
- `RunManifest` for research runs

### media-generation-pipeline owns
- `ScenePlan`
- `MediaPackage`
- `RunManifest` for media runs

## Naming Convention

`<topic_slug>__<artifact_type>__<timestamp>.json`

Example:
`jwst_star_formation_early_universe_demo__ResearchBrief__2026-03-30T120000Z.json`

## Compatibility Rules

Backward-compatible changes:
- add optional fields
- add new artifact types
- expand enums without changing existing values

Breaking changes:
- remove required fields
- rename required fields
- change semantic meaning of core fields
- change artifact type names

Breaking changes require:
- schema version bump
- migration notes
- README update in all three repos
