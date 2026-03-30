"""
Tests for Phase 1.5 bridge: ScenePlan → legacy Scene mapping,
bridge CLI structured-input path, and bridged MediaPackage emission.
"""

import json
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scene_plan_generator import generate_scene_plan, validate_scene_plan, load_research_brief
from media_package_writer import validate_media_package, MEDIA_PACKAGE_REQUIRED_FIELDS, ASSET_REQUIRED_FIELDS
from run_manifest_writer import validate_run_manifest
from bridge_adapter import (
    scene_plan_to_legacy_scenes,
    legacy_scene_to_contract_dict,
    create_bridged_media_package,
)
from scene_manager import Scene
from validate_artifacts import load_contract, validate_artifact


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DEMO_BRIEF_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "demo_data",
    "jwst_star_formation_early_universe_demo",
    "ResearchBrief.sample.json",
)

DEMO_SCENE_PLAN_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "demo_data",
    "jwst_star_formation_early_universe_demo",
    "ScenePlan.sample.json",
)


@pytest.fixture
def sample_brief():
    """Load the canonical JWST demo ResearchBrief."""
    return load_research_brief(DEMO_BRIEF_PATH)


@pytest.fixture
def minimal_brief():
    """A minimal but valid ResearchBrief for unit tests."""
    return {
        "artifact_type": "ResearchBrief",
        "schema_version": "1.0.0",
        "artifact_id": "test-brief-001",
        "created_at": "2026-01-01T00:00:00Z",
        "producer": "test",
        "source_run_id": "test-run",
        "topic": "test_topic",
        "research_question": "What is the test about?",
        "executive_summary": "This is a test executive summary.",
        "key_findings": [
            {"title": "Finding A", "summary": "Detail about A.", "citation_refs": ["ref-1"]},
            {"title": "Finding B", "summary": "Detail about B.", "citation_refs": []},
        ],
        "entities": [
            {"label": "Entity One", "type": "concept"},
            {"label": "Entity Two", "type": "instrument"},
        ],
        "timeline": [
            {"date": "2020", "event": "Project started"},
            {"date": "2022", "event": "First results"},
        ],
        "source_index": [
            {"source_id": "ref-1", "title": "Source One", "url": "https://example.com"},
        ],
        "citation_map": {"ref-1": ["key_findings[0]"]},
        "open_questions": ["What else can we learn?"],
        "recommended_angles": [
            {"angle": "Deep dive", "description": "Go deeper into finding A."},
        ],
    }


@pytest.fixture
def minimal_plan(minimal_brief):
    """Generate a ScenePlan from the minimal brief."""
    return generate_scene_plan(minimal_brief)


@pytest.fixture
def demo_plan(sample_brief):
    """Generate a ScenePlan from the demo brief."""
    return generate_scene_plan(sample_brief)


@pytest.fixture
def contract():
    return load_contract()


# ---------------------------------------------------------------------------
# ScenePlan → Legacy Scene Mapping Tests
# ---------------------------------------------------------------------------

class TestScenePlanToLegacyScenes:
    """Tests for the core bridge mapping from contract ScenePlan to legacy Scene."""

    def test_returns_list_of_scene_dataclass(self, minimal_plan):
        legacy = scene_plan_to_legacy_scenes(minimal_plan)
        assert isinstance(legacy, list)
        assert len(legacy) > 0
        for sc in legacy:
            assert isinstance(sc, Scene)

    def test_scene_count_matches(self, minimal_plan):
        legacy = scene_plan_to_legacy_scenes(minimal_plan)
        assert len(legacy) == len(minimal_plan["scenes"])

    def test_id_mapped_from_scene_id(self, minimal_plan):
        legacy = scene_plan_to_legacy_scenes(minimal_plan)
        for sc, contract_sc in zip(legacy, minimal_plan["scenes"]):
            assert sc.id == contract_sc["scene_id"]

    def test_name_mapped_from_title(self, minimal_plan):
        legacy = scene_plan_to_legacy_scenes(minimal_plan)
        for sc, contract_sc in zip(legacy, minimal_plan["scenes"]):
            assert sc.name == contract_sc["title"]

    def test_prompt_mapped_from_visual_brief(self, minimal_plan):
        legacy = scene_plan_to_legacy_scenes(minimal_plan)
        for sc, contract_sc in zip(legacy, minimal_plan["scenes"]):
            assert sc.prompt == contract_sc["visual_brief"]

    def test_narration_preserved(self, minimal_plan):
        legacy = scene_plan_to_legacy_scenes(minimal_plan)
        for sc, contract_sc in zip(legacy, minimal_plan["scenes"]):
            assert sc.narration == contract_sc["narration"]

    def test_image_and_audio_default_empty(self, minimal_plan):
        legacy = scene_plan_to_legacy_scenes(minimal_plan)
        for sc in legacy:
            assert sc.image_file == ""
            assert sc.audio_file == ""

    def test_demo_brief_bridges_correctly(self, demo_plan):
        legacy = scene_plan_to_legacy_scenes(demo_plan)
        assert len(legacy) >= 3  # at least intro + findings + conclusion
        # First scene should be "Introduction"
        assert legacy[0].name == "Introduction"
        # Last scene should be "Conclusion"
        assert legacy[-1].name == "Conclusion"

    def test_empty_scenes_raises(self):
        bad_plan = {"artifact_type": "ScenePlan", "scenes": []}
        with pytest.raises(ValueError, match="non-empty"):
            scene_plan_to_legacy_scenes(bad_plan)

    def test_missing_scenes_raises(self):
        bad_plan = {"artifact_type": "ScenePlan"}
        with pytest.raises(ValueError, match="non-empty"):
            scene_plan_to_legacy_scenes(bad_plan)


class TestLegacySceneToContractDict:
    """Tests for reverse-mapping a legacy Scene to a contract scene dict."""

    def test_round_trip_preserves_fields(self, minimal_plan):
        legacy = scene_plan_to_legacy_scenes(minimal_plan)
        for sc, original in zip(legacy, minimal_plan["scenes"]):
            contract_dict = legacy_scene_to_contract_dict(sc)
            assert contract_dict["scene_id"] == original["scene_id"]
            assert contract_dict["title"] == original["title"]
            assert contract_dict["visual_brief"] == original["visual_brief"]
            assert contract_dict["narration"] == original["narration"]

    def test_includes_file_paths(self):
        sc = Scene(id="test-1", name="Test", prompt="prompt", narration="narr",
                   image_file="/path/to/img.png", audio_file="/path/to/audio.mp3")
        d = legacy_scene_to_contract_dict(sc)
        assert d["image_file"] == "/path/to/img.png"
        assert d["audio_file"] == "/path/to/audio.mp3"


# ---------------------------------------------------------------------------
# Bridged MediaPackage Emission Tests
# ---------------------------------------------------------------------------

class TestBridgedMediaPackage:
    """Tests for bridged MediaPackage emission with rich render metadata."""

    def test_creates_valid_package_on_dry_run(self, minimal_plan):
        render_result = {
            "success": False,
            "stage": "skipped",
            "error": "Rendering skipped (dry-run mode)",
            "rendered_scenes": scene_plan_to_legacy_scenes(minimal_plan),
            "output_dir": "/tmp/test_output",
            "video_path": "",
        }
        pkg = create_bridged_media_package(minimal_plan, render_result)
        errors = validate_media_package(pkg)
        assert errors == [], f"Validation errors: {errors}"

    def test_package_has_bridge_metadata(self, minimal_plan):
        render_result = {
            "success": False,
            "stage": "content_generator_init",
            "error": "API keys not found",
            "rendered_scenes": scene_plan_to_legacy_scenes(minimal_plan),
            "output_dir": "/tmp/test",
            "video_path": "",
        }
        pkg = create_bridged_media_package(minimal_plan, render_result)
        bridge_meta = pkg["render_manifest"]["bridge"]
        assert bridge_meta["adapter"] == "bridge_adapter.scene_plan_to_legacy_scenes"
        assert bridge_meta["last_stage"] == "content_generator_init"
        assert bridge_meta["success"] is False
        assert "API keys" in bridge_meta["error"]

    def test_package_status_placeholder_on_failure(self, minimal_plan):
        render_result = {
            "success": False,
            "stage": "skipped",
            "error": "skip",
            "rendered_scenes": [],
            "output_dir": "/tmp/test",
            "video_path": "",
        }
        pkg = create_bridged_media_package(minimal_plan, render_result)
        assert pkg["render_manifest"]["status"] == "placeholder"

    def test_package_status_rendered_on_success(self, minimal_plan):
        legacy = scene_plan_to_legacy_scenes(minimal_plan)
        render_result = {
            "success": True,
            "stage": "complete",
            "error": None,
            "rendered_scenes": legacy,
            "output_dir": "/tmp/test",
            "video_path": "/tmp/test/final_video.mp4",
        }
        pkg = create_bridged_media_package(minimal_plan, render_result)
        assert pkg["render_manifest"]["status"] == "rendered"
        assert pkg["render_manifest"]["bridge"]["success"] is True

    def test_video_path_propagated_on_success(self, minimal_plan):
        legacy = scene_plan_to_legacy_scenes(minimal_plan)
        # Simulate rendered files
        legacy[0].image_file = "/tmp/images/scene-001.png"
        legacy[0].audio_file = "/tmp/audio/scene-001.mp3"
        render_result = {
            "success": True,
            "stage": "complete",
            "error": None,
            "rendered_scenes": legacy,
            "output_dir": "/tmp/test",
            "video_path": "/tmp/test/final_video.mp4",
        }
        pkg = create_bridged_media_package(minimal_plan, render_result)
        video_assets = [a for a in pkg["assets"] if a["asset_type"] == "video"]
        assert len(video_assets) == 1
        assert video_assets[0]["local_path"] == "/tmp/test/final_video.mp4"

    def test_contract_validation_passes(self, minimal_plan, contract):
        render_result = {
            "success": False,
            "stage": "skipped",
            "error": "dry-run",
            "rendered_scenes": [],
            "output_dir": "/tmp/test",
            "video_path": "",
        }
        pkg = create_bridged_media_package(minimal_plan, render_result)
        errors = validate_artifact(pkg, contract)
        assert errors == [], f"Contract errors: {errors}"

    def test_assets_count_correct(self, minimal_plan):
        render_result = {
            "success": False,
            "stage": "skipped",
            "error": "dry-run",
            "rendered_scenes": [],
            "output_dir": "/tmp/test",
            "video_path": "",
        }
        pkg = create_bridged_media_package(minimal_plan, render_result)
        num_scenes = len(minimal_plan["scenes"])
        # 2 assets per scene (image + audio) + 1 final video
        assert len(pkg["assets"]) == num_scenes * 2 + 1


# ---------------------------------------------------------------------------
# CLI Structured-Input Path Tests
# ---------------------------------------------------------------------------

class TestBridgeCLI:
    """Tests for the bridge_cli.py entry point."""

    def test_cli_from_research_brief_dry_run(self, tmp_path):
        """CLI accepts a ResearchBrief and emits ScenePlan + MediaPackage in dry-run mode."""
        output_dir = str(tmp_path / "output")
        result = subprocess.run(
            [
                sys.executable, "bridge_cli.py",
                DEMO_BRIEF_PATH,
                "--output-dir", output_dir,
                "--dry-run",
                "--validate",
            ],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        assert result.returncode == 0, f"CLI failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert "VALID" in result.stdout
        # Check output files exist
        files = os.listdir(output_dir)
        assert any("ScenePlan" in f for f in files), f"No ScenePlan in {files}"
        assert any("MediaPackage" in f for f in files), f"No MediaPackage in {files}"
        assert any("RunManifest" in f for f in files), f"No RunManifest in {files}"

    def test_cli_from_scene_plan(self, tmp_path):
        """CLI accepts a ScenePlan directly with --scene-plan flag."""
        output_dir = str(tmp_path / "output")
        result = subprocess.run(
            [
                sys.executable, "bridge_cli.py",
                DEMO_SCENE_PLAN_PATH,
                "--scene-plan",
                "--output-dir", output_dir,
                "--dry-run",
                "--validate",
            ],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        assert result.returncode == 0, f"CLI failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert "VALID" in result.stdout

    def test_cli_invalid_input_returns_nonzero(self, tmp_path):
        """CLI returns non-zero for invalid input."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text('{"artifact_type": "NotABrief"}')
        result = subprocess.run(
            [
                sys.executable, "bridge_cli.py",
                str(bad_file),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        assert result.returncode != 0

    def test_cli_render_flag_without_keys(self, tmp_path):
        """CLI with --render fails gracefully when API keys are missing."""
        output_dir = str(tmp_path / "output")
        # Ensure no API keys are set
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        env.pop("STABILITY_API_KEY", None)
        result = subprocess.run(
            [
                sys.executable, "bridge_cli.py",
                DEMO_BRIEF_PATH,
                "--output-dir", output_dir,
                "--render",
                "--validate",
            ],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
            env=env,
        )
        # Should still succeed (emits placeholder), but report render failure
        assert result.returncode == 0, f"CLI failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert "Rendering stopped" in result.stdout or "VALID" in result.stdout

    def test_cli_output_media_package_has_bridge_metadata(self, tmp_path):
        """The emitted MediaPackage contains bridge render metadata."""
        output_dir = str(tmp_path / "output")
        subprocess.run(
            [
                sys.executable, "bridge_cli.py",
                DEMO_BRIEF_PATH,
                "--output-dir", output_dir,
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        # Find the MediaPackage file
        files = os.listdir(output_dir)
        pkg_files = [f for f in files if "MediaPackage" in f]
        assert len(pkg_files) == 1, f"Expected 1 MediaPackage, found {pkg_files}"
        with open(os.path.join(output_dir, pkg_files[0])) as f:
            pkg = json.load(f)
        assert "bridge" in pkg["render_manifest"]
        assert pkg["render_manifest"]["bridge"]["adapter"] == "bridge_adapter.scene_plan_to_legacy_scenes"

    def test_cli_quiet_mode(self, tmp_path):
        """CLI --quiet suppresses output."""
        output_dir = str(tmp_path / "output")
        result = subprocess.run(
            [
                sys.executable, "bridge_cli.py",
                DEMO_BRIEF_PATH,
                "--output-dir", output_dir,
                "--dry-run",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        assert result.returncode == 0
        # Quiet mode should produce minimal output
        assert len(result.stdout.strip()) == 0
