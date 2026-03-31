"""
Phase 4 Integration Tests: real downstream artifact transport in reusable
workflow mode.

Validates:
 - Downloaded handoff directory is used as input when present (orchestration mode)
 - Committed demo_data fixture is used as fallback (manual mode)
 - --upstream-run-id CLI flag overrides handoff_manifest source_run_id in RunManifest
 - RunManifest records the real input path from the downloaded artifact
 - RunManifest records the real handoff source_run_id from the downloaded artifact
 - When --upstream-run-id is not provided, handoff_manifest source_run_id is used
 - Provenance propagation: source_run_id flows through to RunManifest inputs
 - CLI still works without --upstream-run-id (backward compatibility)
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
    HANDOFF_MANIFEST_FILE,
)
from scene_plan_generator import generate_scene_plan, validate_scene_plan
from media_package_writer import create_media_package, validate_media_package
from run_manifest_writer import create_run_manifest, validate_run_manifest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DEMO_DIR = os.path.join(
    REPO_ROOT, "demo_data", "jwst_star_formation_early_universe_demo"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_handoff_dir(tmp_path, source_run_id="crp-run-real-abc123", topic="test_topic"):
    """Create a minimal handoff directory simulating a real downstream artifact."""
    brief_data = {
        "artifact_type": "ResearchBrief",
        "schema_version": "1.0.0",
        "artifact_id": f"rb-{source_run_id}",
        "created_at": "2026-03-31T00:00:00Z",
        "producer": "content-research-pipeline",
        "source_run_id": source_run_id,
        "topic": topic,
        "research_question": "How does JWST observe star formation?",
        "executive_summary": "JWST enables infrared observation of star-forming regions.",
        "key_findings": [
            {
                "finding": "JWST detects protostars in nebulae.",
                "confidence": "high",
                "citation_refs": ["src-001"],
            }
        ],
        "entities": [
            {"label": "JWST", "type": "instrument"},
            {"label": "Carina Nebula", "type": "location"},
        ],
        "timeline": [],
        "source_index": [
            {"source_id": "src-001", "title": "JWST Early Release", "url": "https://example.com"}
        ],
        "citation_map": {},
        "open_questions": [],
        "recommended_angles": [],
    }

    handoff_dir = tmp_path / "downloaded_handoff"
    handoff_dir.mkdir()

    brief_file = handoff_dir / "ResearchBrief.json"
    brief_file.write_text(json.dumps(brief_data, indent=2))

    manifest_data = {
        "schema_version": "1.0.0",
        "handoff_type": "ResearchBrief",
        "source_pipeline": "content-research-pipeline",
        "source_run_id": source_run_id,
        "created_at": "2026-03-31T00:00:00Z",
        "topic": topic,
        "primary_artifact": "ResearchBrief.json",
        "artifacts": [
            {"artifact_type": "ResearchBrief", "filename": "ResearchBrief.json"}
        ],
    }
    (handoff_dir / HANDOFF_MANIFEST_FILE).write_text(json.dumps(manifest_data, indent=2))

    return str(handoff_dir), source_run_id


# ---------------------------------------------------------------------------
# Path selection: orchestration vs. fixture mode
# ---------------------------------------------------------------------------


class TestPathSelection:
    """Tests that the correct input path is chosen based on context."""

    def test_downloaded_handoff_dir_is_used_when_present(self, tmp_path):
        """When a downloaded handoff directory exists, it should be used as input."""
        handoff_dir, _ = _make_handoff_dir(tmp_path)
        brief, meta = load_handoff_package(handoff_dir)
        assert brief["artifact_type"] == "ResearchBrief"
        assert meta["brief_path"].startswith(handoff_dir)

    def test_demo_fixture_used_as_fallback(self):
        """When no downloaded artifact is present, the committed demo fixture is used."""
        brief, meta = load_handoff_package(DEMO_DIR)
        assert brief["artifact_type"] == "ResearchBrief"
        assert DEMO_DIR in meta["source_path"]

    def test_downloaded_artifact_records_correct_input_path(self, tmp_path):
        """RunManifest inputs.research_brief should point to the downloaded artifact,
        not the committed demo_data path."""
        handoff_dir, _ = _make_handoff_dir(tmp_path)
        _, meta = load_handoff_package(handoff_dir)

        # The brief_path should be inside the downloaded handoff dir
        assert handoff_dir in meta["brief_path"]
        assert "demo_data" not in meta["brief_path"]

    def test_fixture_fallback_records_demo_path(self):
        """In fixture mode, RunManifest inputs should still point to demo_data."""
        _, meta = load_handoff_package(DEMO_DIR)
        assert "demo_data" in meta["brief_path"]


# ---------------------------------------------------------------------------
# Provenance propagation: source_run_id flows through to RunManifest
# ---------------------------------------------------------------------------


class TestProvenancePropagation:
    """Tests that handoff source_run_id is correctly propagated to the RunManifest."""

    def test_run_manifest_records_handoff_source_run_id_from_manifest(self, tmp_path):
        """RunManifest should record the source_run_id from the handoff_manifest.json."""
        real_run_id = "crp-run-orchestrated-xyz789"
        handoff_dir, _ = _make_handoff_dir(tmp_path, source_run_id=real_run_id)
        brief, meta = load_handoff_package(handoff_dir)
        scene_plan = generate_scene_plan(brief)

        # Build inputs as generate_scene_plan.py does
        inputs_dict = {"research_brief": meta["brief_path"]}
        if meta.get("handoff_manifest"):
            hm = meta["handoff_manifest"]
            if hm.get("source_pipeline"):
                inputs_dict["handoff_source_pipeline"] = hm["source_pipeline"]
            if hm.get("source_run_id"):
                inputs_dict["handoff_source_run_id"] = hm["source_run_id"]

        manifest = create_run_manifest(
            pipeline_stage="scene_plan_generation",
            status="complete",
            inputs=inputs_dict,
            outputs=[],
            metrics={"num_scenes": len(scene_plan["scenes"])},
            source_run_id=scene_plan["source_run_id"],
        )

        assert manifest["inputs"]["handoff_source_run_id"] == real_run_id
        assert manifest["inputs"]["handoff_source_pipeline"] == "content-research-pipeline"

    def test_upstream_run_id_overrides_manifest_source_run_id(self, tmp_path):
        """When --upstream-run-id is provided, it should override the handoff_manifest's
        source_run_id in the RunManifest inputs."""
        manifest_run_id = "crp-run-from-manifest"
        override_run_id = "github-actions-run-999"

        handoff_dir, _ = _make_handoff_dir(tmp_path, source_run_id=manifest_run_id)
        brief, meta = load_handoff_package(handoff_dir)
        scene_plan = generate_scene_plan(brief)

        # Build inputs as generate_scene_plan.py does
        inputs_dict = {"research_brief": meta["brief_path"]}
        if meta.get("handoff_manifest"):
            hm = meta["handoff_manifest"]
            if hm.get("source_pipeline"):
                inputs_dict["handoff_source_pipeline"] = hm["source_pipeline"]
            if hm.get("source_run_id"):
                inputs_dict["handoff_source_run_id"] = hm["source_run_id"]

        # Simulate --upstream-run-id override
        inputs_dict["handoff_source_run_id"] = override_run_id

        manifest = create_run_manifest(
            pipeline_stage="scene_plan_generation",
            status="complete",
            inputs=inputs_dict,
            outputs=[],
            metrics={"num_scenes": len(scene_plan["scenes"])},
            source_run_id=scene_plan["source_run_id"],
        )

        assert manifest["inputs"]["handoff_source_run_id"] == override_run_id
        assert manifest["inputs"]["handoff_source_run_id"] != manifest_run_id

    def test_without_upstream_override_manifest_run_id_preserved(self, tmp_path):
        """Without --upstream-run-id, the handoff_manifest's source_run_id is used."""
        manifest_run_id = "crp-run-preserved-original"
        handoff_dir, _ = _make_handoff_dir(tmp_path, source_run_id=manifest_run_id)
        brief, meta = load_handoff_package(handoff_dir)
        scene_plan = generate_scene_plan(brief)

        inputs_dict = {"research_brief": meta["brief_path"]}
        if meta.get("handoff_manifest"):
            hm = meta["handoff_manifest"]
            if hm.get("source_pipeline"):
                inputs_dict["handoff_source_pipeline"] = hm["source_pipeline"]
            if hm.get("source_run_id"):
                inputs_dict["handoff_source_run_id"] = hm["source_run_id"]

        # No override applied
        manifest = create_run_manifest(
            pipeline_stage="scene_plan_generation",
            status="complete",
            inputs=inputs_dict,
            outputs=[],
            metrics={"num_scenes": len(scene_plan["scenes"])},
            source_run_id=scene_plan["source_run_id"],
        )

        assert manifest["inputs"]["handoff_source_run_id"] == manifest_run_id

    def test_different_orchestration_runs_produce_different_provenance(self, tmp_path):
        """Two different orchestration runs should produce RunManifests with
        different handoff_source_run_id values."""
        run_a_dir = tmp_path / "run_a"
        run_a_dir.mkdir()
        run_b_dir = tmp_path / "run_b"
        run_b_dir.mkdir()

        dir_a, _ = _make_handoff_dir(
            run_a_dir, source_run_id="crp-run-alpha", topic="alpha_topic"
        )
        dir_b, _ = _make_handoff_dir(
            run_b_dir, source_run_id="crp-run-beta", topic="beta_topic"
        )

        _, meta_a = load_handoff_package(dir_a)
        _, meta_b = load_handoff_package(dir_b)

        assert meta_a["handoff_manifest"]["source_run_id"] != \
               meta_b["handoff_manifest"]["source_run_id"]


# ---------------------------------------------------------------------------
# CLI integration: --upstream-run-id flag
# ---------------------------------------------------------------------------


class TestCLIUpstreamRunId:
    """CLI tests for the --upstream-run-id flag in generate_scene_plan.py."""

    def test_cli_with_upstream_run_id(self, tmp_path):
        """CLI with --upstream-run-id records the override in the RunManifest."""
        override_id = "orchestration-stage2-run-42"
        result = subprocess.run(
            [
                sys.executable,
                "generate_scene_plan.py",
                DEMO_DIR,
                "--output-dir", str(tmp_path / "generated"),
                "--stable-output",
                "--media-package",
                "--validate",
                "--upstream-run-id", override_id,
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

        # Check the generated RunManifest in the timestamped output dir
        gen_dir = str(tmp_path / "generated")
        manifest_files = [f for f in os.listdir(gen_dir) if "RunManifest" in f]
        assert len(manifest_files) == 1
        with open(os.path.join(gen_dir, manifest_files[0])) as f:
            manifest = json.load(f)

        assert manifest["inputs"]["handoff_source_run_id"] == override_id

    def test_cli_without_upstream_run_id(self, tmp_path):
        """CLI without --upstream-run-id uses handoff_manifest source_run_id."""
        result = subprocess.run(
            [
                sys.executable,
                "generate_scene_plan.py",
                DEMO_DIR,
                "--output-dir", str(tmp_path / "generated"),
                "--media-package",
                "--validate",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, (
            f"CLI failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        gen_dir = str(tmp_path / "generated")
        manifest_files = [f for f in os.listdir(gen_dir) if "RunManifest" in f]
        assert len(manifest_files) == 1
        with open(os.path.join(gen_dir, manifest_files[0])) as f:
            manifest = json.load(f)

        # Should use the demo handoff_manifest source_run_id
        assert manifest["inputs"]["handoff_source_run_id"] == "crp-run-jwst-demo"

    def test_cli_with_downloaded_handoff_dir(self, tmp_path):
        """CLI with a simulated downloaded handoff directory records the correct
        input path and provenance."""
        handoff_dir, run_id = _make_handoff_dir(tmp_path)
        result = subprocess.run(
            [
                sys.executable,
                "generate_scene_plan.py",
                handoff_dir,
                "--output-dir", str(tmp_path / "generated"),
                "--media-package",
                "--validate",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, (
            f"CLI failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        gen_dir = str(tmp_path / "generated")
        manifest_files = [f for f in os.listdir(gen_dir) if "RunManifest" in f]
        assert len(manifest_files) == 1
        with open(os.path.join(gen_dir, manifest_files[0])) as f:
            manifest = json.load(f)

        # Input path should point into the downloaded handoff dir
        assert handoff_dir in manifest["inputs"]["research_brief"]
        assert "demo_data" not in manifest["inputs"]["research_brief"]

        # Provenance should match the handoff manifest
        assert manifest["inputs"]["handoff_source_run_id"] == run_id
        assert manifest["inputs"]["handoff_source_pipeline"] == "content-research-pipeline"

    def test_cli_downloaded_dir_with_upstream_override(self, tmp_path):
        """CLI with downloaded handoff dir AND --upstream-run-id uses the override."""
        manifest_run_id = "crp-run-from-downloaded-manifest"
        override_id = "explicit-orchestrator-run-99"
        handoff_dir, _ = _make_handoff_dir(tmp_path, source_run_id=manifest_run_id)

        result = subprocess.run(
            [
                sys.executable,
                "generate_scene_plan.py",
                handoff_dir,
                "--output-dir", str(tmp_path / "generated"),
                "--media-package",
                "--validate",
                "--upstream-run-id", override_id,
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, (
            f"CLI failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        gen_dir = str(tmp_path / "generated")
        manifest_files = [f for f in os.listdir(gen_dir) if "RunManifest" in f]
        with open(os.path.join(gen_dir, manifest_files[0])) as f:
            manifest = json.load(f)

        # Upstream override takes precedence
        assert manifest["inputs"]["handoff_source_run_id"] == override_id
        assert manifest["inputs"]["handoff_source_run_id"] != manifest_run_id


# ---------------------------------------------------------------------------
# End-to-end: simulated orchestration run
# ---------------------------------------------------------------------------


class TestOrchestrationEndToEnd:
    """End-to-end tests simulating the full orchestration flow:
    download artifact → generate → validate → check provenance."""

    def test_full_orchestration_flow(self, tmp_path):
        """Simulate the complete orchestration flow: a downloaded handoff
        artifact is consumed, generating valid outputs with correct provenance."""
        real_run_id = "crp-run-orchestration-e2e-test"
        handoff_dir, _ = _make_handoff_dir(tmp_path, source_run_id=real_run_id)

        result = subprocess.run(
            [
                sys.executable,
                "generate_scene_plan.py",
                handoff_dir,
                "--output-dir", str(tmp_path / "generated"),
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

        # Verify the RunManifest in timestamped output
        gen_dir = str(tmp_path / "generated")
        manifest_files = [f for f in os.listdir(gen_dir) if "RunManifest" in f]
        assert len(manifest_files) == 1
        with open(os.path.join(gen_dir, manifest_files[0])) as f:
            manifest = json.load(f)

        # Provenance: real run ID, not the demo fixture value
        assert manifest["inputs"]["handoff_source_run_id"] == real_run_id
        assert manifest["inputs"]["handoff_source_run_id"] != "crp-run-jwst-demo"
        assert manifest["inputs"]["handoff_source_pipeline"] == "content-research-pipeline"

        # Input path: the downloaded handoff dir, not demo_data
        assert handoff_dir in manifest["inputs"]["research_brief"]
        assert "demo_data" not in manifest["inputs"]["research_brief"]

    def test_orchestration_with_upstream_override(self, tmp_path):
        """Orchestration flow with explicit --upstream-run-id override."""
        manifest_run_id = "crp-run-manifest-value"
        override_run_id = "github-run-override-value"
        handoff_dir, _ = _make_handoff_dir(tmp_path, source_run_id=manifest_run_id)

        result = subprocess.run(
            [
                sys.executable,
                "generate_scene_plan.py",
                handoff_dir,
                "--output-dir", str(tmp_path / "generated"),
                "--media-package",
                "--validate",
                "--upstream-run-id", override_run_id,
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, (
            f"CLI failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        gen_dir = str(tmp_path / "generated")
        manifest_files = [f for f in os.listdir(gen_dir) if "RunManifest" in f]
        with open(os.path.join(gen_dir, manifest_files[0])) as f:
            manifest = json.load(f)

        assert manifest["inputs"]["handoff_source_run_id"] == override_run_id

    def test_manual_mode_still_works(self, tmp_path):
        """Manual mode (no downloaded artifact) continues to work as before."""
        result = subprocess.run(
            [
                sys.executable,
                "generate_scene_plan.py",
                DEMO_DIR,
                "--output-dir", str(tmp_path / "generated"),
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

        gen_dir = str(tmp_path / "generated")
        manifest_files = [f for f in os.listdir(gen_dir) if "RunManifest" in f]
        with open(os.path.join(gen_dir, manifest_files[0])) as f:
            manifest = json.load(f)

        # In manual mode, should still use the demo handoff_manifest run id
        assert manifest["inputs"]["handoff_source_run_id"] == "crp-run-jwst-demo"
