# JWST Demo Scaffold

This folder is the canonical demo scaffold for all three repositories.

It intentionally contains:
- a source manifest
- directory structure for multimodal inputs
- empty output folders for ingestion / research / media artifacts
- starter placeholders for Codex-assisted retrieval

It does not bundle raw external NASA/ESA assets.

## Intended demo question

How does the James Webb Space Telescope help us understand star formation and the early universe?

## Happy-path source pack

- NASA mission overview
- NASA fact sheet
- NASA infographic / diagram reference
- NASA image gallery index
- NASA Webb star-formation video reference
- ESA Webb brochure reference

## Next step for Codex

1. Read `manifest.json`
2. Download or normalize the listed sources into the matching `sources/` subfolders
3. Emit `RawSourceBundle`, `NormalizedDocumentSet`, `ChunkSet`, and `KnowledgeGraphPackage`
4. Feed the graph and normalized content into research and media modules
