# Canonical ResearchBrief Fixtures

This directory contains canonical ResearchBrief fixtures that simulate
artifacts produced by `content-research-pipeline`.

These fixtures are used for:
- Integration testing of the handoff from content-research to media-generation
- Validating that ScenePlan generation preserves provenance/citation references
- Ensuring the pipeline works end-to-end without requiring upstream runs

## Files

| Fixture | Description |
|---------|-------------|
| `jwst_canonical.json` | Canonical JWST star formation / early universe demo brief |

## Contract

All fixtures conform to the `ResearchBrief` schema defined in
`contracts/shared_artifacts.json` (schema version 1.0.0).

Required fields: `artifact_type`, `schema_version`, `artifact_id`,
`created_at`, `producer`, `source_run_id`, `topic`, `research_question`,
`executive_summary`, `key_findings`, `entities`, `timeline`, `source_index`,
`citation_map`, `open_questions`, `recommended_angles`.

## Provenance Chain

The citation provenance chain through the pipeline is:

```
ResearchBrief.source_index[].source_id
    ↓ referenced by
ResearchBrief.key_findings[].citation_refs[]
    ↓ propagated to
ScenePlan.scenes[].citation_refs[]
```

This chain must be preserved by the media-generation-pipeline when
converting a ResearchBrief into a ScenePlan.
