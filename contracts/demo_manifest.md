# Demo Manifest
Schema version: 1.0.0

Canonical topic:
- `jwst_star_formation_early_universe_demo`

Canonical source bundle:
- NASA + ESA Webb starter pack

Seed entities:
- James Webb Space Telescope
- infrared astronomy
- L2 orbit
- sunshield
- primary mirror
- star formation
- early universe
- galaxies
- exoplanets
- spectroscopy

Primary artifact flow:
- `RawSourceBundle`
- `NormalizedDocumentSet`
- `ChunkSet`
- `KnowledgeGraphPackage`
- `ResearchBrief`
- `ScenePlan`
- `MediaPackage`

Happy-path demo:
1. Ingest mission pages, fact sheet, gallery metadata, one video transcript, one ESA PDF
2. Build graph + embeddings + provenance
3. Generate research brief on “How Webb reveals star formation and the early universe”
4. Generate short explainer scene plan + media output
