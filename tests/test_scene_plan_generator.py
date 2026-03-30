"""
Tests for the Phase 1 happy path: ScenePlan generation from ResearchBrief.

Tests scene_plan_generator, media_package_writer, run_manifest_writer,
and validate_artifacts modules.
"""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scene_plan_generator import (
    generate_scene_plan,
    load_research_brief,
    validate_scene_plan,
    SCENE_PLAN_REQUIRED_FIELDS,
    SCENE_REQUIRED_FIELDS,
)
from media_package_writer import (
    create_media_package,
    validate_media_package,
    save_media_package,
)
from run_manifest_writer import (
    create_run_manifest,
    validate_run_manifest,
    save_run_manifest,
)
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
def contract():
    """Load the shared artifact contract."""
    return load_contract()


# ---------------------------------------------------------------------------
# ScenePlan Generator Tests
# ---------------------------------------------------------------------------

class TestLoadResearchBrief:
    """Tests for loading and validating ResearchBrief files."""

    def test_load_demo_brief(self, sample_brief):
        assert sample_brief["artifact_type"] == "ResearchBrief"
        assert sample_brief["topic"] == "jwst_star_formation_early_universe_demo"
        assert len(sample_brief["key_findings"]) > 0

    def test_load_invalid_artifact_type(self, tmp_path):
        bad = {"artifact_type": "NotABrief", "schema_version": "1.0.0"}
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(bad))
        with pytest.raises(ValueError, match="Expected artifact_type"):
            load_research_brief(str(path))

    def test_load_missing_fields(self, tmp_path):
        incomplete = {"artifact_type": "ResearchBrief"}
        path = tmp_path / "incomplete.json"
        path.write_text(json.dumps(incomplete))
        with pytest.raises(ValueError, match="missing required fields"):
            load_research_brief(str(path))

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_research_brief("/nonexistent/path.json")


class TestGenerateScenePlan:
    """Tests for ScenePlan generation from a ResearchBrief."""

    def test_generates_valid_scene_plan(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        errors = validate_scene_plan(plan)
        assert errors == [], f"Validation errors: {errors}"

    def test_scene_plan_has_required_fields(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        for field in SCENE_PLAN_REQUIRED_FIELDS:
            assert field in plan, f"Missing field: {field}"

    def test_scenes_have_required_fields(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        for scene in plan["scenes"]:
            for field in SCENE_REQUIRED_FIELDS:
                assert field in scene, f"Scene missing field: {field}"

    def test_generates_scenes_from_findings(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        # Should have: intro + 2 findings + timeline + conclusion = 5
        assert len(plan["scenes"]) == 5

    def test_narrative_goal_from_research_question(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        assert plan["narrative_goal"] == "What is the test about?"

    def test_custom_narrative_goal(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief, narrative_goal="Custom goal")
        assert plan["narrative_goal"] == "Custom goal"

    def test_custom_target_audience(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief, target_audience="PhD students")
        assert plan["target_audience"] == "PhD students"

    def test_custom_style_profile(self, minimal_brief):
        style = {"tone": "playful", "visual_style": "cartoon"}
        plan = generate_scene_plan(minimal_brief, style_profile=style)
        assert plan["style_profile"] == style

    def test_topic_carried_through(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        assert plan["topic"] == "test_topic"

    def test_artifact_type_is_scene_plan(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        assert plan["artifact_type"] == "ScenePlan"

    def test_intro_scene_uses_executive_summary(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        intro = plan["scenes"][0]
        assert intro["title"] == "Introduction"
        assert "test executive summary" in intro["narration"]

    def test_conclusion_scene_present(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        conclusion = plan["scenes"][-1]
        assert conclusion["title"] == "Conclusion"
        assert conclusion["transition"] == "fade_out"

    def test_entity_refs_populated(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        intro = plan["scenes"][0]
        assert "Entity One" in intro["entity_refs"]

    def test_citation_refs_from_findings(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        # Second scene is first finding, which has citation_refs
        finding_scene = plan["scenes"][1]
        assert "ref-1" in finding_scene["citation_refs"]

    def test_demo_brief_produces_valid_plan(self, sample_brief):
        plan = generate_scene_plan(sample_brief)
        errors = validate_scene_plan(plan)
        assert errors == [], f"Validation errors: {errors}"
        assert len(plan["scenes"]) >= 3

    def test_empty_findings_still_valid(self):
        brief = {
            "artifact_type": "ResearchBrief",
            "schema_version": "1.0.0",
            "artifact_id": "empty-brief",
            "created_at": "2026-01-01T00:00:00Z",
            "producer": "test",
            "source_run_id": "test",
            "topic": "empty_topic",
            "research_question": "What?",
            "executive_summary": "",
            "key_findings": [],
            "entities": [],
            "timeline": [],
            "source_index": [],
            "citation_map": {},
            "open_questions": [],
            "recommended_angles": [],
        }
        plan = generate_scene_plan(brief)
        errors = validate_scene_plan(plan)
        assert errors == []
        # Should still have at least intro + conclusion
        assert len(plan["scenes"]) >= 2


class TestValidateScenePlan:
    """Tests for ScenePlan validation."""

    def test_valid_plan_passes(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        assert validate_scene_plan(plan) == []

    def test_missing_artifact_type(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        del plan["artifact_type"]
        errors = validate_scene_plan(plan)
        assert any("artifact_type" in e for e in errors)

    def test_wrong_artifact_type(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        plan["artifact_type"] = "WrongType"
        errors = validate_scene_plan(plan)
        assert any("ScenePlan" in e for e in errors)

    def test_missing_scene_field(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        del plan["scenes"][0]["narration"]
        errors = validate_scene_plan(plan)
        assert any("narration" in e for e in errors)

    def test_demo_scene_plan_sample_valid(self, contract):
        with open(DEMO_SCENE_PLAN_PATH) as f:
            plan = json.load(f)
        errors = validate_artifact(plan, contract)
        assert errors == [], f"Demo ScenePlan.sample.json invalid: {errors}"


# ---------------------------------------------------------------------------
# MediaPackage Writer Tests
# ---------------------------------------------------------------------------

class TestMediaPackageWriter:
    """Tests for MediaPackage generation."""

    def test_creates_valid_package(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        pkg = create_media_package(plan)
        errors = validate_media_package(pkg)
        assert errors == [], f"Validation errors: {errors}"

    def test_placeholder_flag(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        pkg = create_media_package(plan, rendered=False)
        assert pkg["render_manifest"]["status"] == "placeholder"

    def test_rendered_flag(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        pkg = create_media_package(plan, rendered=True)
        assert pkg["render_manifest"]["status"] == "rendered"

    def test_assets_include_video(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        pkg = create_media_package(plan)
        video_assets = [a for a in pkg["assets"] if a["asset_type"] == "video"]
        assert len(video_assets) == 1

    def test_assets_per_scene(self, minimal_brief):
        plan = generate_scene_plan(minimal_brief)
        pkg = create_media_package(plan)
        num_scenes = len(plan["scenes"])
        # 2 assets per scene (image + audio) + 1 final video
        assert len(pkg["assets"]) == num_scenes * 2 + 1

    def test_save_and_reload(self, minimal_brief, tmp_path):
        plan = generate_scene_plan(minimal_brief)
        pkg = create_media_package(plan)
        path = str(tmp_path / "pkg.json")
        save_media_package(pkg, path)

        with open(path) as f:
            reloaded = json.load(f)
        assert reloaded["artifact_type"] == "MediaPackage"

    def test_contract_validation(self, minimal_brief, contract):
        plan = generate_scene_plan(minimal_brief)
        pkg = create_media_package(plan)
        errors = validate_artifact(pkg, contract)
        assert errors == [], f"Contract errors: {errors}"


# ---------------------------------------------------------------------------
# RunManifest Writer Tests
# ---------------------------------------------------------------------------

class TestRunManifestWriter:
    """Tests for RunManifest generation."""

    def test_creates_valid_manifest(self):
        manifest = create_run_manifest(
            pipeline_stage="scene_plan_generation",
            status="complete",
            inputs={"research_brief": "path/to/brief.json"},
        )
        errors = validate_run_manifest(manifest)
        assert errors == [], f"Validation errors: {errors}"

    def test_has_required_fields(self):
        manifest = create_run_manifest(
            pipeline_stage="test",
            status="running",
            inputs={},
        )
        from run_manifest_writer import RUN_MANIFEST_REQUIRED_FIELDS

        for field in RUN_MANIFEST_REQUIRED_FIELDS:
            assert field in manifest

    def test_custom_run_id(self):
        manifest = create_run_manifest(
            pipeline_stage="test",
            status="complete",
            inputs={},
            source_run_id="custom-run-id",
        )
        assert manifest["source_run_id"] == "custom-run-id"

    def test_save_and_reload(self, tmp_path):
        manifest = create_run_manifest(
            pipeline_stage="test",
            status="complete",
            inputs={"topic": "test"},
        )
        path = str(tmp_path / "manifest.json")
        save_run_manifest(manifest, path)

        with open(path) as f:
            reloaded = json.load(f)
        assert reloaded["artifact_type"] == "RunManifest"

    def test_contract_validation(self, contract):
        manifest = create_run_manifest(
            pipeline_stage="test",
            status="complete",
            inputs={},
        )
        errors = validate_artifact(manifest, contract)
        assert errors == [], f"Contract errors: {errors}"


# ---------------------------------------------------------------------------
# Contract Validator Tests
# ---------------------------------------------------------------------------

class TestContractValidator:
    """Tests for the general-purpose artifact validator."""

    def test_load_contract(self, contract):
        assert "artifacts" in contract
        assert "ScenePlan" in contract["artifacts"]
        assert "MediaPackage" in contract["artifacts"]
        assert "RunManifest" in contract["artifacts"]

    def test_validate_demo_research_brief(self, contract):
        with open(DEMO_BRIEF_PATH) as f:
            brief = json.load(f)
        errors = validate_artifact(brief, contract)
        assert errors == [], f"Demo ResearchBrief invalid: {errors}"

    def test_validate_unknown_type(self, contract):
        artifact = {"artifact_type": "UnknownType"}
        errors = validate_artifact(artifact, contract)
        assert any("Unknown" in e for e in errors)

    def test_validate_missing_type(self, contract):
        errors = validate_artifact({}, contract)
        assert any("artifact_type" in e for e in errors)
