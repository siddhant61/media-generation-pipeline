"""
Phase 2A Integration Tests: ResearchBrief handoff from content-research-pipeline.

Validates:
 - Canonical JWST fixture can be loaded via the fixture path
 - ScenePlan generation from canonical fixture is contract-valid
 - Citation/provenance references are preserved across the handoff
 - Entity references are carried into ScenePlan scenes
 - MediaPackage placeholder emission works from fixture input
 - Full CLI dry-run pipeline works from fixture input
 - All generated artifacts validate against the shared contract
"""

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scene_plan_generator import (
    generate_scene_plan,
    load_research_brief,
    load_research_brief_fixture,
    list_research_brief_fixtures,
    validate_scene_plan,
    FIXTURES_DIR,
)
from media_package_writer import (
    create_media_package,
    validate_media_package,
    save_media_package,
)
from run_manifest_writer import (
    create_run_manifest,
    validate_run_manifest,
)
from bridge_adapter import (
    scene_plan_to_legacy_scenes,
    create_bridged_media_package,
)
from validate_artifacts import load_contract, validate_artifact


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CANONICAL_FIXTURE_NAME = "jwst_canonical"

CANONICAL_FIXTURE_PATH = os.path.join(
    FIXTURES_DIR,
    f"{CANONICAL_FIXTURE_NAME}.json",
)


@pytest.fixture
def canonical_brief():
    """Load the canonical JWST ResearchBrief fixture."""
    return load_research_brief_fixture(CANONICAL_FIXTURE_NAME)


@pytest.fixture
def canonical_plan(canonical_brief):
    """Generate a ScenePlan from the canonical fixture."""
    return generate_scene_plan(canonical_brief)


@pytest.fixture
def contract():
    """Load the shared artifact contract."""
    return load_contract()


# ---------------------------------------------------------------------------
# Fixture Loading Tests
# ---------------------------------------------------------------------------

class TestFixtureLoading:
    """Tests for the canonical fixture loading path."""

    def test_fixtures_dir_exists(self):
        assert os.path.isdir(FIXTURES_DIR), f"Fixtures dir missing: {FIXTURES_DIR}"

    def test_canonical_fixture_exists(self):
        assert os.path.isfile(CANONICAL_FIXTURE_PATH), (
            f"Canonical fixture missing: {CANONICAL_FIXTURE_PATH}"
        )

    def test_list_fixtures_includes_canonical(self):
        fixtures = list_research_brief_fixtures()
        assert CANONICAL_FIXTURE_NAME in fixtures

    def test_load_fixture_by_name(self, canonical_brief):
        assert canonical_brief["artifact_type"] == "ResearchBrief"
        assert canonical_brief["topic"] == "jwst_star_formation_early_universe_demo"

    def test_load_fixture_with_json_extension(self):
        brief = load_research_brief_fixture(f"{CANONICAL_FIXTURE_NAME}.json")
        assert brief["artifact_type"] == "ResearchBrief"

    def test_load_nonexistent_fixture_raises(self):
        with pytest.raises(FileNotFoundError):
            load_research_brief_fixture("nonexistent_fixture")

    def test_fixture_producer_is_content_research(self, canonical_brief):
        assert canonical_brief["producer"] == "content-research-pipeline"

    def test_fixture_has_source_run_id(self, canonical_brief):
        assert canonical_brief["source_run_id"] != ""
        assert "crp" in canonical_brief["source_run_id"]  # content-research-pipeline


# ---------------------------------------------------------------------------
# ScenePlan Generation from Fixture
# ---------------------------------------------------------------------------

class TestScenePlanFromFixture:
    """Tests that ScenePlan generation from canonical fixture is contract-valid."""

    def test_generates_valid_plan(self, canonical_plan):
        errors = validate_scene_plan(canonical_plan)
        assert errors == [], f"Validation errors: {errors}"

    def test_plan_has_correct_topic(self, canonical_plan):
        assert canonical_plan["topic"] == "jwst_star_formation_early_universe_demo"

    def test_plan_has_scenes(self, canonical_plan):
        assert len(canonical_plan["scenes"]) >= 3  # intro + findings + conclusion

    def test_plan_artifact_type(self, canonical_plan):
        assert canonical_plan["artifact_type"] == "ScenePlan"

    def test_plan_producer(self, canonical_plan):
        assert canonical_plan["producer"] == "media-generation-pipeline"

    def test_intro_scene_uses_executive_summary(self, canonical_brief, canonical_plan):
        intro = canonical_plan["scenes"][0]
        assert intro["title"] == "Introduction"
        # Executive summary text should be in the narration
        assert "James Webb Space Telescope" in intro["narration"]

    def test_finding_scenes_generated(self, canonical_brief, canonical_plan):
        findings = canonical_brief["key_findings"]
        # Each finding should map to a scene (up to 4)
        finding_scenes = [
            s for s in canonical_plan["scenes"]
            if s["title"] not in ("Introduction", "Conclusion", "Timeline")
        ]
        assert len(finding_scenes) == min(len(findings), 4)

    def test_conclusion_scene_present(self, canonical_plan):
        conclusion = canonical_plan["scenes"][-1]
        assert conclusion["title"] == "Conclusion"
        assert conclusion["transition"] == "fade_out"

    def test_contract_validation(self, canonical_plan, contract):
        errors = validate_artifact(canonical_plan, contract)
        assert errors == [], f"Contract validation errors: {errors}"


# ---------------------------------------------------------------------------
# Provenance / Citation Preservation Tests
# ---------------------------------------------------------------------------

class TestProvenancePreservation:
    """Verify citation and provenance references survive the handoff."""

    def test_citation_refs_propagated_to_finding_scenes(
        self, canonical_brief, canonical_plan
    ):
        """Each finding scene should carry the citation_refs from its source finding."""
        findings = canonical_brief["key_findings"]
        # Scenes 1..N-1 (skip intro at 0, skip timeline/conclusion at end)
        for i, finding in enumerate(findings[:4]):
            scene = canonical_plan["scenes"][i + 1]  # +1 to skip intro
            expected_refs = finding.get("citation_refs", [])
            assert scene["citation_refs"] == expected_refs, (
                f"Scene '{scene['title']}' citation_refs mismatch: "
                f"expected {expected_refs}, got {scene['citation_refs']}"
            )

    def test_all_citation_refs_are_valid_source_ids(
        self, canonical_brief, canonical_plan
    ):
        """Every citation_ref in ScenePlan scenes should exist in the brief's source_index."""
        source_ids = {s["source_id"] for s in canonical_brief["source_index"]}
        for scene in canonical_plan["scenes"]:
            for ref in scene["citation_refs"]:
                assert ref in source_ids, (
                    f"Scene '{scene['title']}' has citation_ref '{ref}' "
                    f"not found in source_index {source_ids}"
                )

    def test_citation_map_coverage(self, canonical_brief, canonical_plan):
        """All source_ids used in citation_refs should appear in citation_map."""
        citation_map = canonical_brief.get("citation_map", {})
        all_refs = set()
        for scene in canonical_plan["scenes"]:
            all_refs.update(scene["citation_refs"])
        for ref in all_refs:
            assert ref in citation_map, (
                f"citation_ref '{ref}' not found in citation_map keys"
            )

    def test_source_run_id_carried_through(self, canonical_brief, canonical_plan):
        """The source_run_id should link back to the research pipeline."""
        # The plan uses a generated run_id, but source_run_id parameter
        # can be explicitly set to trace back to the research run
        plan_with_provenance = generate_scene_plan(
            canonical_brief,
            source_run_id=canonical_brief["source_run_id"],
        )
        assert plan_with_provenance["source_run_id"] == canonical_brief["source_run_id"]


# ---------------------------------------------------------------------------
# Entity Reference Preservation Tests
# ---------------------------------------------------------------------------

class TestEntityPreservation:
    """Verify entity references from ResearchBrief flow into ScenePlan."""

    def test_entity_refs_in_intro_scene(self, canonical_brief, canonical_plan):
        """Introduction scene should reference entities from the brief."""
        entity_labels = [
            e.get("label", e) if isinstance(e, dict) else str(e)
            for e in canonical_brief.get("entities", [])
        ]
        intro = canonical_plan["scenes"][0]
        assert len(intro["entity_refs"]) > 0
        for ref in intro["entity_refs"]:
            assert ref in entity_labels, (
                f"entity_ref '{ref}' not found in brief entities"
            )

    def test_entity_refs_in_finding_scenes(self, canonical_brief, canonical_plan):
        """Finding scenes should carry entity references."""
        entity_labels = [
            e.get("label", e) if isinstance(e, dict) else str(e)
            for e in canonical_brief.get("entities", [])
        ]
        finding_scenes = canonical_plan["scenes"][1:-1]  # skip intro and conclusion
        for scene in finding_scenes:
            if scene["title"] != "Timeline":
                assert len(scene["entity_refs"]) > 0, (
                    f"Scene '{scene['title']}' has no entity_refs"
                )
                for ref in scene["entity_refs"]:
                    assert ref in entity_labels


# ---------------------------------------------------------------------------
# MediaPackage Placeholder Emission Tests
# ---------------------------------------------------------------------------

class TestMediaPackageFromFixture:
    """Test MediaPackage placeholder emission from canonical fixture input."""

    def test_placeholder_package_valid(self, canonical_plan):
        pkg = create_media_package(canonical_plan, rendered=False)
        errors = validate_media_package(pkg)
        assert errors == [], f"Validation errors: {errors}"

    def test_placeholder_status(self, canonical_plan):
        pkg = create_media_package(canonical_plan, rendered=False)
        assert pkg["render_manifest"]["status"] == "placeholder"

    def test_placeholder_contract_validation(self, canonical_plan, contract):
        pkg = create_media_package(canonical_plan, rendered=False)
        errors = validate_artifact(pkg, contract)
        assert errors == [], f"Contract errors: {errors}"

    def test_bridged_placeholder_valid(self, canonical_plan):
        render_result = {
            "success": False,
            "stage": "skipped",
            "error": "Rendering skipped (API-gated: requires OPENAI_API_KEY and STABILITY_API_KEY)",
            "rendered_scenes": scene_plan_to_legacy_scenes(canonical_plan),
            "output_dir": "/tmp/test_output",
            "video_path": "",
        }
        pkg = create_bridged_media_package(canonical_plan, render_result)
        errors = validate_media_package(pkg)
        assert errors == [], f"Validation errors: {errors}"
        assert pkg["render_manifest"]["status"] == "placeholder"
        assert "bridge" in pkg["render_manifest"]

    def test_bridged_placeholder_contract_validation(self, canonical_plan, contract):
        render_result = {
            "success": False,
            "stage": "skipped",
            "error": "dry-run",
            "rendered_scenes": [],
            "output_dir": "/tmp/test",
            "video_path": "",
        }
        pkg = create_bridged_media_package(canonical_plan, render_result)
        errors = validate_artifact(pkg, contract)
        assert errors == [], f"Contract errors: {errors}"

    def test_package_topic_matches(self, canonical_plan):
        pkg = create_media_package(canonical_plan)
        assert pkg["topic"] == canonical_plan["topic"]


# ---------------------------------------------------------------------------
# CLI Pipeline Integration Tests
# ---------------------------------------------------------------------------

class TestCLIPipelineFromFixture:
    """Test the full CLI pipeline using canonical fixture input."""

    def test_generate_scene_plan_cli(self, tmp_path):
        """generate_scene_plan.py works with canonical fixture."""
        output_dir = str(tmp_path / "output")
        result = subprocess.run(
            [
                sys.executable, "generate_scene_plan.py",
                CANONICAL_FIXTURE_PATH,
                "--output-dir", output_dir,
                "--media-package",
                "--validate",
            ],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        assert result.returncode == 0, (
            f"CLI failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "All artifacts valid" in result.stdout

        # Verify output files
        files = os.listdir(output_dir)
        assert any("ScenePlan" in f for f in files)
        assert any("MediaPackage" in f for f in files)
        assert any("RunManifest" in f for f in files)

    def test_bridge_cli_dry_run(self, tmp_path):
        """bridge_cli.py works with canonical fixture in dry-run mode."""
        output_dir = str(tmp_path / "output")
        result = subprocess.run(
            [
                sys.executable, "bridge_cli.py",
                CANONICAL_FIXTURE_PATH,
                "--output-dir", output_dir,
                "--dry-run",
                "--validate",
            ],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        assert result.returncode == 0, (
            f"CLI failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "VALID" in result.stdout

    def test_cli_output_scene_plan_is_contract_valid(self, tmp_path):
        """ScenePlan emitted by CLI validates against the shared contract."""
        output_dir = str(tmp_path / "output")
        subprocess.run(
            [
                sys.executable, "generate_scene_plan.py",
                CANONICAL_FIXTURE_PATH,
                "--output-dir", output_dir,
                "--validate",
            ],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        contract = load_contract()
        files = os.listdir(output_dir)
        plan_files = [f for f in files if "ScenePlan" in f]
        assert len(plan_files) == 1
        with open(os.path.join(output_dir, plan_files[0])) as f:
            plan = json.load(f)
        errors = validate_artifact(plan, contract)
        assert errors == [], f"Contract errors: {errors}"

    def test_cli_output_preserves_citation_refs(self, tmp_path):
        """ScenePlan emitted by CLI preserves citation references."""
        output_dir = str(tmp_path / "output")
        subprocess.run(
            [
                sys.executable, "generate_scene_plan.py",
                CANONICAL_FIXTURE_PATH,
                "--output-dir", output_dir,
            ],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        files = os.listdir(output_dir)
        plan_files = [f for f in files if "ScenePlan" in f]
        with open(os.path.join(output_dir, plan_files[0])) as f:
            plan = json.load(f)

        # Collect all citation_refs from scenes
        all_refs = set()
        for scene in plan["scenes"]:
            all_refs.update(scene.get("citation_refs", []))

        # The canonical fixture has citation_refs on its findings
        assert len(all_refs) > 0, "No citation_refs found in output ScenePlan"
        # All refs should be valid source_ids from the fixture
        brief = load_research_brief_fixture(CANONICAL_FIXTURE_NAME)
        source_ids = {s["source_id"] for s in brief["source_index"]}
        for ref in all_refs:
            assert ref in source_ids


# ---------------------------------------------------------------------------
# RunManifest Tracking Tests
# ---------------------------------------------------------------------------

class TestRunManifestFromFixture:
    """Test RunManifest generation tracks fixture-sourced runs correctly."""

    def test_manifest_records_input_fixture(self, canonical_plan):
        manifest = create_run_manifest(
            pipeline_stage="scene_plan_generation",
            status="complete",
            inputs={"research_brief_fixture": CANONICAL_FIXTURE_NAME},
            outputs=[],
            metrics={"num_scenes": len(canonical_plan["scenes"])},
            source_run_id=canonical_plan["source_run_id"],
        )
        errors = validate_run_manifest(manifest)
        assert errors == [], f"Validation errors: {errors}"
        assert manifest["inputs"]["research_brief_fixture"] == CANONICAL_FIXTURE_NAME


# ---------------------------------------------------------------------------
# Canonical Fixture Contract Validation
# ---------------------------------------------------------------------------

class TestFixtureContractValidation:
    """Validate the canonical fixture itself against the shared contract."""

    def test_fixture_validates_as_research_brief(self, canonical_brief, contract):
        errors = validate_artifact(canonical_brief, contract)
        assert errors == [], f"Fixture contract errors: {errors}"

    def test_fixture_has_all_required_fields(self, canonical_brief):
        from scene_plan_generator import RESEARCH_BRIEF_REQUIRED_FIELDS
        for field in RESEARCH_BRIEF_REQUIRED_FIELDS:
            assert field in canonical_brief, f"Missing field: {field}"
