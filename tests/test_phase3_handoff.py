"""
Phase 3 Integration Tests: consume canonical downstream handoff package from
content-research-pipeline and emit stable outputs.

Validates:
 - handoff_manifest.json is detected and loaded from a handoff directory
 - primary_artifact field in handoff_manifest.json resolves to the ResearchBrief
 - package_meta["handoff_manifest"] is populated with manifest contents
 - sibling_files list excludes handoff_manifest.json itself
 - missing primary_artifact file raises FileNotFoundError
 - invalid JSON in handoff_manifest.json raises ValueError
 - full end-to-end pipeline: handoff dir → ScenePlan → MediaPackage → RunManifest
 - stable outputs are written to outputs/<topic_slug>/ from a handoff_manifest.json package
 - HandoffManifest is NOT a shared artifact type (operational descriptor only)
"""

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research_brief_handoff import (
    load_handoff_manifest,
    load_handoff_package,
    find_research_brief_in_dir,
    emit_stable_outputs,
    list_stable_outputs,
    HANDOFF_MANIFEST_FILE,
)
from scene_plan_generator import generate_scene_plan, validate_scene_plan
from media_package_writer import create_media_package, validate_media_package
from run_manifest_writer import create_run_manifest, validate_run_manifest
from validate_artifacts import load_contract, validate_artifact

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DEMO_DIR = os.path.join(
    REPO_ROOT, "demo_data", "jwst_star_formation_early_universe_demo"
)
DEMO_HANDOFF_MANIFEST = os.path.join(DEMO_DIR, HANDOFF_MANIFEST_FILE)

CANONICAL_TOPIC = "jwst_star_formation_early_universe_demo"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def contract():
    return load_contract()


@pytest.fixture
def demo_brief_and_meta():
    """Load the demo ResearchBrief via the handoff directory (with handoff_manifest.json)."""
    brief, meta = load_handoff_package(DEMO_DIR)
    return brief, meta


@pytest.fixture
def demo_scene_plan(demo_brief_and_meta):
    brief, _ = demo_brief_and_meta
    return generate_scene_plan(brief)


# ---------------------------------------------------------------------------
# handoff_manifest.json loading
# ---------------------------------------------------------------------------


class TestHandoffManifestLoading:
    """Tests for load_handoff_manifest()."""

    def test_demo_handoff_manifest_exists(self):
        assert os.path.isfile(DEMO_HANDOFF_MANIFEST), (
            f"Demo handoff manifest missing: {DEMO_HANDOFF_MANIFEST}"
        )

    def test_load_handoff_manifest_from_demo_dir(self):
        manifest = load_handoff_manifest(DEMO_DIR)
        assert manifest is not None, "Expected manifest to be loaded"

    def test_handoff_manifest_required_fields(self):
        manifest = load_handoff_manifest(DEMO_DIR)
        for field in [
            "schema_version",
            "handoff_type",
            "source_pipeline",
            "source_run_id",
            "created_at",
            "topic",
            "primary_artifact",
            "artifacts",
        ]:
            assert field in manifest, f"Missing required field: {field}"

    def test_handoff_manifest_source_pipeline(self):
        manifest = load_handoff_manifest(DEMO_DIR)
        assert manifest["source_pipeline"] == "content-research-pipeline"

    def test_handoff_manifest_handoff_type(self):
        manifest = load_handoff_manifest(DEMO_DIR)
        assert manifest["handoff_type"] == "ResearchBrief"

    def test_handoff_manifest_topic(self):
        manifest = load_handoff_manifest(DEMO_DIR)
        assert manifest["topic"] == CANONICAL_TOPIC

    def test_handoff_manifest_primary_artifact_is_str(self):
        manifest = load_handoff_manifest(DEMO_DIR)
        assert isinstance(manifest["primary_artifact"], str)
        assert manifest["primary_artifact"].endswith(".json")

    def test_handoff_manifest_artifacts_is_list(self):
        manifest = load_handoff_manifest(DEMO_DIR)
        assert isinstance(manifest["artifacts"], list)
        assert len(manifest["artifacts"]) >= 1

    def test_handoff_manifest_artifacts_have_type_and_filename(self):
        manifest = load_handoff_manifest(DEMO_DIR)
        for artifact in manifest["artifacts"]:
            assert "artifact_type" in artifact
            assert "filename" in artifact

    def test_handoff_manifest_includes_research_brief_artifact(self):
        manifest = load_handoff_manifest(DEMO_DIR)
        types = [a["artifact_type"] for a in manifest["artifacts"]]
        assert "ResearchBrief" in types

    def test_load_handoff_manifest_returns_none_for_missing(self, tmp_path):
        result = load_handoff_manifest(str(tmp_path))
        assert result is None

    def test_load_handoff_manifest_raises_on_invalid_json(self, tmp_path):
        bad = tmp_path / HANDOFF_MANIFEST_FILE
        bad.write_text("{ not valid json")
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_handoff_manifest(str(tmp_path))


# ---------------------------------------------------------------------------
# find_research_brief_in_dir — Priority 0 (handoff_manifest.json)
# ---------------------------------------------------------------------------


class TestFindResearchBriefWithManifest:
    """Tests for Priority 0 (handoff_manifest.json) in find_research_brief_in_dir()."""

    def test_manifest_primary_artifact_takes_priority(self, tmp_path):
        """handoff_manifest.json primary_artifact is used before filename heuristics."""
        # Create a fake ResearchBrief with a non-standard name
        brief_data = {
            "artifact_type": "ResearchBrief",
            "schema_version": "1.0.0",
            "artifact_id": "test-001",
            "created_at": "2026-01-01T00:00:00Z",
            "producer": "content-research-pipeline",
            "source_run_id": "run-001",
            "topic": "test_topic",
            "research_question": "Test?",
            "executive_summary": "Summary",
            "key_findings": [],
            "entities": [],
            "timeline": [],
            "source_index": [],
            "citation_map": {},
            "open_questions": [],
            "recommended_angles": [],
        }
        brief_file = tmp_path / "canonical_output_brief.json"
        brief_file.write_text(json.dumps(brief_data))

        manifest_data = {
            "schema_version": "1.0.0",
            "handoff_type": "ResearchBrief",
            "source_pipeline": "content-research-pipeline",
            "source_run_id": "run-001",
            "created_at": "2026-01-01T00:00:00Z",
            "topic": "test_topic",
            "primary_artifact": "canonical_output_brief.json",
            "artifacts": [
                {"artifact_type": "ResearchBrief", "filename": "canonical_output_brief.json"}
            ],
        }
        (tmp_path / HANDOFF_MANIFEST_FILE).write_text(json.dumps(manifest_data))

        result = find_research_brief_in_dir(str(tmp_path))
        assert os.path.basename(result) == "canonical_output_brief.json"

    def test_manifest_missing_primary_file_raises(self, tmp_path):
        """If primary_artifact file is declared but missing, FileNotFoundError is raised."""
        manifest_data = {
            "schema_version": "1.0.0",
            "handoff_type": "ResearchBrief",
            "source_pipeline": "content-research-pipeline",
            "source_run_id": "run-001",
            "created_at": "2026-01-01T00:00:00Z",
            "topic": "test_topic",
            "primary_artifact": "nonexistent.json",
            "artifacts": [],
        }
        (tmp_path / HANDOFF_MANIFEST_FILE).write_text(json.dumps(manifest_data))
        with pytest.raises(FileNotFoundError, match="primary_artifact"):
            find_research_brief_in_dir(str(tmp_path))

    def test_demo_dir_resolves_to_research_brief(self):
        result = find_research_brief_in_dir(DEMO_DIR)
        brief_data = json.loads(open(result).read())
        assert brief_data.get("artifact_type") == "ResearchBrief"

    def test_handoff_manifest_not_included_in_filename_heuristics(self, tmp_path):
        """handoff_manifest.json itself should not be considered a ResearchBrief candidate."""
        # Create a dir with only handoff_manifest.json and no ResearchBrief
        manifest_data = {
            "schema_version": "1.0.0",
            "handoff_type": "ResearchBrief",
            "source_pipeline": "content-research-pipeline",
            "source_run_id": "run-001",
            "created_at": "2026-01-01T00:00:00Z",
            "topic": "test_topic",
            "primary_artifact": "ResearchBrief.json",
            "artifacts": [],
        }
        (tmp_path / HANDOFF_MANIFEST_FILE).write_text(json.dumps(manifest_data))
        # primary_artifact file is missing → should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            find_research_brief_in_dir(str(tmp_path))


# ---------------------------------------------------------------------------
# load_handoff_package — Phase 3 package_meta
# ---------------------------------------------------------------------------


class TestLoadHandoffPackagePhase3:
    """Tests for Phase 3 handoff_manifest.json support in load_handoff_package()."""

    def test_package_meta_includes_handoff_manifest(self, demo_brief_and_meta):
        _, meta = demo_brief_and_meta
        assert "handoff_manifest" in meta
        assert meta["handoff_manifest"] is not None

    def test_package_meta_handoff_manifest_contents(self, demo_brief_and_meta):
        _, meta = demo_brief_and_meta
        hm = meta["handoff_manifest"]
        assert hm["source_pipeline"] == "content-research-pipeline"
        assert hm["topic"] == CANONICAL_TOPIC
        assert "primary_artifact" in hm

    def test_package_meta_handoff_manifest_none_for_file_input(self):
        brief_path = os.path.join(DEMO_DIR, "ResearchBrief.sample.json")
        _, meta = load_handoff_package(brief_path)
        assert meta["handoff_manifest"] is None

    def test_sibling_files_excludes_handoff_manifest(self, demo_brief_and_meta):
        _, meta = demo_brief_and_meta
        assert HANDOFF_MANIFEST_FILE not in meta["sibling_files"]

    def test_brief_is_valid_research_brief(self, demo_brief_and_meta):
        brief, _ = demo_brief_and_meta
        assert brief["artifact_type"] == "ResearchBrief"
        assert brief["topic"] == CANONICAL_TOPIC

    def test_handoff_manifest_source_run_id_accessible(self, demo_brief_and_meta):
        _, meta = demo_brief_and_meta
        hm = meta["handoff_manifest"]
        assert hm.get("source_run_id") == "crp-run-jwst-demo"

    def test_handoff_manifest_artifacts_list_accessible(self, demo_brief_and_meta):
        _, meta = demo_brief_and_meta
        hm = meta["handoff_manifest"]
        artifact_types = [a["artifact_type"] for a in hm["artifacts"]]
        assert "ResearchBrief" in artifact_types


# ---------------------------------------------------------------------------
# Phase 3 end-to-end: handoff package → stable outputs
# ---------------------------------------------------------------------------


class TestPhase3EndToEnd:
    """End-to-end tests for Phase 3 happy path: handoff dir → stable outputs."""

    def test_scene_plan_generated_from_handoff_dir(self, demo_scene_plan):
        assert demo_scene_plan["artifact_type"] == "ScenePlan"
        assert len(demo_scene_plan["scenes"]) > 0

    def test_scene_plan_is_contract_valid(self, demo_scene_plan, contract):
        errors = validate_artifact(demo_scene_plan, contract)
        assert errors == [], f"ScenePlan validation errors: {errors}"

    def test_stable_outputs_written_from_handoff_package(
        self, demo_brief_and_meta, tmp_path
    ):
        brief, _ = demo_brief_and_meta
        scene_plan = generate_scene_plan(brief)
        media_package = create_media_package(scene_plan, rendered=False)
        run_manifest = create_run_manifest(
            pipeline_stage="scene_plan_generation",
            status="complete",
            inputs={"research_brief": DEMO_DIR},
            outputs=[],
            metrics={"num_scenes": len(scene_plan["scenes"])},
            source_run_id=scene_plan["source_run_id"],
        )

        paths = emit_stable_outputs(
            scene_plan, media_package, run_manifest, base_dir=str(tmp_path)
        )

        assert "ScenePlan" in paths
        assert "MediaPackage" in paths
        assert "RunManifest" in paths
        for p in paths.values():
            assert os.path.isfile(p), f"Expected output file: {p}"

    def test_stable_outputs_are_contract_valid(
        self, demo_brief_and_meta, tmp_path, contract
    ):
        brief, _ = demo_brief_and_meta
        scene_plan = generate_scene_plan(brief)
        media_package = create_media_package(scene_plan, rendered=False)
        run_manifest = create_run_manifest(
            pipeline_stage="scene_plan_generation",
            status="complete",
            inputs={"research_brief": DEMO_DIR},
            outputs=[],
            metrics={"num_scenes": len(scene_plan["scenes"])},
            source_run_id=scene_plan["source_run_id"],
        )

        paths = emit_stable_outputs(
            scene_plan, media_package, run_manifest, base_dir=str(tmp_path)
        )

        for artifact_type, path in paths.items():
            artifact = json.loads(open(path).read())
            errors = validate_artifact(artifact, contract)
            assert errors == [], f"{artifact_type} has validation errors: {errors}"

    def test_stable_outputs_topic_dir_matches_brief_topic(
        self, demo_brief_and_meta, tmp_path
    ):
        brief, _ = demo_brief_and_meta
        scene_plan = generate_scene_plan(brief)
        media_package = create_media_package(scene_plan, rendered=False)
        run_manifest = create_run_manifest(
            pipeline_stage="scene_plan_generation",
            status="complete",
            inputs={"research_brief": DEMO_DIR},
            outputs=[],
            metrics={"num_scenes": len(scene_plan["scenes"])},
            source_run_id=scene_plan["source_run_id"],
        )

        paths = emit_stable_outputs(
            scene_plan, media_package, run_manifest, base_dir=str(tmp_path)
        )

        scene_plan_dir = os.path.dirname(paths["ScenePlan"])
        assert os.path.basename(scene_plan_dir) == CANONICAL_TOPIC

    def test_stable_outputs_listed_after_writing(
        self, demo_brief_and_meta, tmp_path
    ):
        brief, _ = demo_brief_and_meta
        scene_plan = generate_scene_plan(brief)
        media_package = create_media_package(scene_plan, rendered=False)
        run_manifest = create_run_manifest(
            pipeline_stage="scene_plan_generation",
            status="complete",
            inputs={"research_brief": DEMO_DIR},
            outputs=[],
            metrics={"num_scenes": len(scene_plan["scenes"])},
            source_run_id=scene_plan["source_run_id"],
        )

        emit_stable_outputs(
            scene_plan, media_package, run_manifest, base_dir=str(tmp_path)
        )

        listed = list_stable_outputs(CANONICAL_TOPIC, base_dir=str(tmp_path))
        assert "ScenePlan" in listed
        assert "MediaPackage" in listed
        assert "RunManifest" in listed

    def test_cli_handoff_dir_with_stable_output(self, tmp_path):
        """CLI: generate_scene_plan.py <handoff_dir> --stable-output --media-package --validate"""
        result = subprocess.run(
            [
                sys.executable,
                "generate_scene_plan.py",
                DEMO_DIR,
                "--output-dir",
                str(tmp_path / "generated"),
                "--stable-output",
                "--media-package",
                "--validate",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            env={
                **os.environ,
                "MEDIA_PIPELINE_OUTPUTS_DIR": str(tmp_path / "outputs"),
            },
        )
        assert result.returncode == 0, (
            f"CLI failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "VALID" in result.stdout or "valid" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Contract: HandoffManifest is NOT a shared artifact type
# ---------------------------------------------------------------------------


class TestHandoffManifestNotInContract:
    """Validates that HandoffManifest is an operational descriptor, not a shared artifact."""

    def test_handoff_manifest_not_in_shared_artifacts(self, contract):
        """handoff_manifest.json is an operational package descriptor, not a formal
        shared artifact type.  It must not appear in contracts/shared_artifacts.json."""
        assert "HandoffManifest" not in contract.get("artifacts", {}), (
            "HandoffManifest should not be in contracts/shared_artifacts.json — "
            "it is an operational package descriptor, not a shared artifact type"
        )

    def test_handoff_manifest_file_still_loads(self):
        """Operational handoff_manifest.json loading still works even though it
        is not a shared artifact type."""
        manifest = load_handoff_manifest(DEMO_DIR)
        assert manifest is not None
        assert "primary_artifact" in manifest
        assert "artifacts" in manifest
