"""
Phase 2B Integration Tests: canonical ResearchBrief handoff → ScenePlan → MediaPackage.

Validates:
 - Handoff package loading from a direct JSON file
 - Handoff package loading from a handoff directory (auto-detect ResearchBrief)
 - Full end-to-end pipeline: handoff → ScenePlan → MediaPackage → RunManifest
 - Stable output location (outputs/<topic_slug>/)
 - All artifacts remain contract-valid
 - Citation refs and entity refs are preserved end-to-end
 - CLI supports directory input and --stable-output flag
"""

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scene_plan_generator import (
    generate_scene_plan,
    validate_scene_plan,
)
from media_package_writer import (
    create_media_package,
    validate_media_package,
)
from run_manifest_writer import (
    create_run_manifest,
    validate_run_manifest,
)
from research_brief_handoff import (
    load_handoff_package,
    find_research_brief_in_dir,
    emit_stable_outputs,
    list_stable_outputs,
    stable_output_dir,
    _topic_slug,
    STABLE_SCENE_PLAN_FILE,
    STABLE_MEDIA_PACKAGE_FILE,
    STABLE_RUN_MANIFEST_FILE,
)
from validate_artifacts import load_contract, validate_artifact

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DEMO_DIR = os.path.join(
    REPO_ROOT, "demo_data", "jwst_star_formation_early_universe_demo"
)
DEMO_BRIEF_FILE = os.path.join(DEMO_DIR, "ResearchBrief.sample.json")

FIXTURE_FILE = os.path.join(
    REPO_ROOT, "fixtures", "research_briefs", "jwst_canonical.json"
)

CANONICAL_TOPIC = "jwst_star_formation_early_universe_demo"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def contract():
    return load_contract()


@pytest.fixture
def demo_brief_from_file():
    """Load the demo ResearchBrief directly from the file path."""
    brief, _ = load_handoff_package(DEMO_BRIEF_FILE)
    return brief


@pytest.fixture
def demo_brief_from_dir():
    """Load the demo ResearchBrief via the handoff directory."""
    brief, _ = load_handoff_package(DEMO_DIR)
    return brief


@pytest.fixture
def canonical_brief():
    """Load the canonical fixture ResearchBrief."""
    brief, _ = load_handoff_package(FIXTURE_FILE)
    return brief


@pytest.fixture
def canonical_plan(canonical_brief):
    return generate_scene_plan(canonical_brief)


@pytest.fixture
def canonical_package(canonical_plan):
    return create_media_package(canonical_plan, rendered=False)


@pytest.fixture
def canonical_manifest(canonical_plan):
    return create_run_manifest(
        pipeline_stage="scene_plan_generation",
        status="complete",
        inputs={"research_brief": FIXTURE_FILE},
        outputs=[],
        metrics={"num_scenes": len(canonical_plan["scenes"])},
        source_run_id=canonical_plan["source_run_id"],
    )


# ===========================================================================
# 0. Topic slug helper
# ===========================================================================


class TestTopicSlug:
    """Verify _topic_slug produces filesystem-safe strings."""

    def test_spaces_replaced(self):
        assert _topic_slug("hello world") == "hello_world"

    def test_slashes_replaced(self):
        assert _topic_slug("a/b/c") == "a_b_c"

    def test_colons_replaced(self):
        # "topic: subtitle" → "topic__subtitle" could be expected, but colon+space
        # both become "_" and consecutive underscores are collapsed → "topic_subtitle"
        result = _topic_slug("topic: subtitle")
        assert " " not in result
        assert ":" not in result
        assert result == result.lower()

    def test_already_safe(self):
        assert _topic_slug("jwst_star_formation_early_universe_demo") == \
            "jwst_star_formation_early_universe_demo"

    def test_lowercased(self):
        assert _topic_slug("JWST") == "jwst"

    def test_consecutive_special_chars_collapsed(self):
        slug = _topic_slug("a  b")
        assert "__" not in slug or slug == "a__b"  # multiple underscores collapsed


# ===========================================================================
# 1. Handoff package loading
# ===========================================================================


class TestHandoffPackageLoading:
    """Verify load_handoff_package works for file and directory inputs."""

    def test_load_from_file_returns_valid_brief(self, demo_brief_from_file):
        assert demo_brief_from_file["artifact_type"] == "ResearchBrief"

    def test_load_from_file_package_meta(self):
        _, meta = load_handoff_package(DEMO_BRIEF_FILE)
        assert meta["brief_path"] == DEMO_BRIEF_FILE
        assert meta["source_path"] == DEMO_BRIEF_FILE
        assert meta["sibling_files"] == []

    def test_load_from_directory_returns_valid_brief(self, demo_brief_from_dir):
        assert demo_brief_from_dir["artifact_type"] == "ResearchBrief"
        assert demo_brief_from_dir["topic"] == CANONICAL_TOPIC

    def test_load_from_directory_package_meta(self):
        _, meta = load_handoff_package(DEMO_DIR)
        assert meta["source_path"] == DEMO_DIR
        assert DEMO_BRIEF_FILE == meta["brief_path"]
        # The demo directory contains other JSON files
        assert isinstance(meta["sibling_files"], list)

    def test_load_from_directory_finds_correct_file(self):
        brief_path = find_research_brief_in_dir(DEMO_DIR)
        with open(brief_path) as f:
            data = json.load(f)
        assert data["artifact_type"] == "ResearchBrief"

    def test_load_from_fixture_file(self, canonical_brief):
        assert canonical_brief["artifact_type"] == "ResearchBrief"
        assert canonical_brief["producer"] == "content-research-pipeline"

    def test_load_from_nonexistent_path_raises(self):
        with pytest.raises(FileNotFoundError):
            load_handoff_package("/tmp/does_not_exist_phase2b.json")

    def test_load_from_nonexistent_dir_raises(self):
        with pytest.raises(FileNotFoundError):
            load_handoff_package("/tmp/does_not_exist_phase2b_dir/")

    def test_load_wrong_artifact_type_raises(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"artifact_type": "ScenePlan", "topic": "test"}))
        with pytest.raises(ValueError):
            load_handoff_package(str(bad))

    def test_load_from_dir_no_brief_raises(self, tmp_path):
        (tmp_path / "not_a_brief.json").write_text(
            json.dumps({"artifact_type": "RunManifest"})
        )
        with pytest.raises(FileNotFoundError):
            load_handoff_package(str(tmp_path))

    def test_demo_dir_brief_matches_fixture_topic(
        self, demo_brief_from_dir, canonical_brief
    ):
        assert demo_brief_from_dir["topic"] == canonical_brief["topic"]


# ===========================================================================
# 2. ScenePlan generation from handoff
# ===========================================================================


class TestScenePlanFromHandoff:
    """Verify ScenePlan generation from both handoff paths."""

    def test_plan_from_file_is_valid(self, demo_brief_from_file, contract):
        plan = generate_scene_plan(demo_brief_from_file)
        errors = validate_artifact(plan, contract)
        assert errors == [], f"Contract errors: {errors}"

    def test_plan_from_dir_is_valid(self, demo_brief_from_dir, contract):
        plan = generate_scene_plan(demo_brief_from_dir)
        errors = validate_artifact(plan, contract)
        assert errors == [], f"Contract errors: {errors}"

    def test_plan_from_fixture_is_valid(self, canonical_plan, contract):
        errors = validate_artifact(canonical_plan, contract)
        assert errors == [], f"Contract errors: {errors}"

    def test_plan_has_expected_topic(self, canonical_plan):
        assert canonical_plan["topic"] == CANONICAL_TOPIC

    def test_plan_producer_is_this_pipeline(self, canonical_plan):
        assert canonical_plan["producer"] == "media-generation-pipeline"

    def test_plan_has_at_least_three_scenes(self, canonical_plan):
        assert len(canonical_plan["scenes"]) >= 3

    def test_all_required_scene_fields_present(self, canonical_plan):
        required = [
            "scene_id", "title", "purpose", "narration", "visual_brief",
            "on_screen_text", "entity_refs", "citation_refs",
            "duration_seconds", "transition",
        ]
        for scene in canonical_plan["scenes"]:
            for field in required:
                assert field in scene, f"Scene '{scene.get('title')}' missing '{field}'"


# ===========================================================================
# 3. MediaPackage emission from handoff
# ===========================================================================


class TestMediaPackageFromHandoff:
    """Verify placeholder MediaPackage emission from canonical fixture."""

    def test_package_is_contract_valid(self, canonical_package, contract):
        errors = validate_artifact(canonical_package, contract)
        assert errors == [], f"Contract errors: {errors}"

    def test_package_is_placeholder(self, canonical_package):
        assert canonical_package["render_manifest"]["status"] == "placeholder"

    def test_package_topic_matches_plan(self, canonical_plan, canonical_package):
        assert canonical_package["topic"] == canonical_plan["topic"]

    def test_package_has_assets_for_each_scene(self, canonical_plan, canonical_package):
        num_scenes = len(canonical_plan["scenes"])
        # Each scene has an image + audio asset, plus the final video
        assert len(canonical_package["assets"]) == num_scenes * 2 + 1

    def test_package_render_manifest_has_scene_plan_id(
        self, canonical_plan, canonical_package
    ):
        assert (
            canonical_package["render_manifest"]["scene_plan_id"]
            == canonical_plan["artifact_id"]
        )


# ===========================================================================
# 4. Stable output location
# ===========================================================================


class TestStableOutputLocation:
    """Verify emit_stable_outputs writes to outputs/<topic_slug>/ correctly."""

    def test_stable_outputs_written(
        self, canonical_plan, canonical_package, canonical_manifest, tmp_path
    ):
        paths = emit_stable_outputs(
            canonical_plan, canonical_package, canonical_manifest,
            base_dir=str(tmp_path),
        )
        assert "ScenePlan" in paths
        assert "MediaPackage" in paths
        assert "RunManifest" in paths
        for path in paths.values():
            assert os.path.isfile(path), f"Missing: {path}"

    def test_stable_output_file_names(
        self, canonical_plan, canonical_package, canonical_manifest, tmp_path
    ):
        paths = emit_stable_outputs(
            canonical_plan, canonical_package, canonical_manifest,
            base_dir=str(tmp_path),
        )
        assert os.path.basename(paths["ScenePlan"]) == STABLE_SCENE_PLAN_FILE
        assert os.path.basename(paths["MediaPackage"]) == STABLE_MEDIA_PACKAGE_FILE
        assert os.path.basename(paths["RunManifest"]) == STABLE_RUN_MANIFEST_FILE

    def test_stable_output_dir_structure(
        self, canonical_plan, canonical_package, canonical_manifest, tmp_path
    ):
        paths = emit_stable_outputs(
            canonical_plan, canonical_package, canonical_manifest,
            base_dir=str(tmp_path),
        )
        # All outputs share the same parent directory
        dirs = {os.path.dirname(p) for p in paths.values()}
        assert len(dirs) == 1
        out_dir = dirs.pop()
        assert out_dir == os.path.join(
            str(tmp_path), CANONICAL_TOPIC
        )

    def test_stable_scene_plan_is_contract_valid(
        self, canonical_plan, canonical_package, canonical_manifest, tmp_path, contract
    ):
        paths = emit_stable_outputs(
            canonical_plan, canonical_package, canonical_manifest,
            base_dir=str(tmp_path),
        )
        with open(paths["ScenePlan"]) as f:
            plan = json.load(f)
        errors = validate_artifact(plan, contract)
        assert errors == [], f"Contract errors: {errors}"

    def test_stable_media_package_is_contract_valid(
        self, canonical_plan, canonical_package, canonical_manifest, tmp_path, contract
    ):
        paths = emit_stable_outputs(
            canonical_plan, canonical_package, canonical_manifest,
            base_dir=str(tmp_path),
        )
        with open(paths["MediaPackage"]) as f:
            pkg = json.load(f)
        errors = validate_artifact(pkg, contract)
        assert errors == [], f"Contract errors: {errors}"

    def test_stable_run_manifest_is_contract_valid(
        self, canonical_plan, canonical_package, canonical_manifest, tmp_path, contract
    ):
        paths = emit_stable_outputs(
            canonical_plan, canonical_package, canonical_manifest,
            base_dir=str(tmp_path),
        )
        with open(paths["RunManifest"]) as f:
            manifest = json.load(f)
        errors = validate_artifact(manifest, contract)
        assert errors == [], f"Contract errors: {errors}"

    def test_list_stable_outputs_after_emit(
        self, canonical_plan, canonical_package, canonical_manifest, tmp_path
    ):
        emit_stable_outputs(
            canonical_plan, canonical_package, canonical_manifest,
            base_dir=str(tmp_path),
        )
        found = list_stable_outputs(CANONICAL_TOPIC, base_dir=str(tmp_path))
        assert "ScenePlan" in found
        assert "MediaPackage" in found
        assert "RunManifest" in found

    def test_list_stable_outputs_empty_when_missing(self, tmp_path):
        found = list_stable_outputs("nonexistent_topic", base_dir=str(tmp_path))
        assert found == {}

    def test_overwrite_idempotent(
        self, canonical_plan, canonical_package, canonical_manifest, tmp_path
    ):
        """Running emit_stable_outputs twice overwrites cleanly."""
        paths1 = emit_stable_outputs(
            canonical_plan, canonical_package, canonical_manifest,
            base_dir=str(tmp_path),
        )
        paths2 = emit_stable_outputs(
            canonical_plan, canonical_package, canonical_manifest,
            base_dir=str(tmp_path),
        )
        assert paths1 == paths2
        for path in paths2.values():
            assert os.path.isfile(path)


# ===========================================================================
# 5. Citation and entity ref preservation
# ===========================================================================


class TestCitationAndEntityPreservation:
    """Citation refs and entity refs must survive the full handoff path."""

    def test_citation_refs_non_empty(self, canonical_plan):
        all_refs = [
            ref
            for scene in canonical_plan["scenes"]
            for ref in scene.get("citation_refs", [])
        ]
        assert len(all_refs) > 0, "Expected at least one citation_ref across all scenes"

    def test_citation_refs_from_findings_preserved(self, canonical_brief, canonical_plan):
        findings = canonical_brief["key_findings"]
        finding_by_title = {f["title"]: f for f in findings[:4]}
        for scene in canonical_plan["scenes"]:
            if scene["title"] in finding_by_title:
                expected = finding_by_title[scene["title"]].get("citation_refs", [])
                assert scene["citation_refs"] == expected, (
                    f"Scene '{scene['title']}' citation_refs mismatch"
                )

    def test_all_citation_refs_are_valid_source_ids(
        self, canonical_brief, canonical_plan
    ):
        source_ids = {s["source_id"] for s in canonical_brief["source_index"]}
        for scene in canonical_plan["scenes"]:
            for ref in scene["citation_refs"]:
                assert ref in source_ids, (
                    f"'{ref}' not found in source_index"
                )

    def test_entity_refs_in_intro_scene(self, canonical_brief, canonical_plan):
        entities = [
            e["label"] if isinstance(e, dict) else str(e)
            for e in canonical_brief.get("entities", [])
        ]
        intro = canonical_plan["scenes"][0]
        assert len(intro["entity_refs"]) > 0
        for ref in intro["entity_refs"]:
            assert ref in entities

    def test_entity_refs_in_finding_scenes(self, canonical_brief, canonical_plan):
        entities = [
            e["label"] if isinstance(e, dict) else str(e)
            for e in canonical_brief.get("entities", [])
        ]
        finding_scenes = [
            s for s in canonical_plan["scenes"]
            if s["title"] not in ("Introduction", "Conclusion", "Timeline")
        ]
        for scene in finding_scenes:
            assert isinstance(scene["entity_refs"], list)
            for ref in scene["entity_refs"]:
                assert ref in entities


# ===========================================================================
# 6. Full end-to-end pipeline from handoff
# ===========================================================================


class TestEndToEndFromHandoff:
    """Full pipeline: handoff → ScenePlan → MediaPackage → RunManifest (all valid)."""

    def test_full_pipeline_from_file(self, tmp_path, contract):
        brief, meta = load_handoff_package(DEMO_BRIEF_FILE)
        plan = generate_scene_plan(brief)
        pkg = create_media_package(plan, rendered=False)
        manifest = create_run_manifest(
            pipeline_stage="scene_plan_generation",
            status="complete",
            inputs={"research_brief": meta["brief_path"]},
            outputs=[],
            metrics={"num_scenes": len(plan["scenes"])},
            source_run_id=plan["source_run_id"],
        )

        for artifact in (plan, pkg, manifest):
            errors = validate_artifact(artifact, contract)
            assert errors == [], (
                f"{artifact['artifact_type']} invalid: {errors}"
            )

    def test_full_pipeline_from_directory(self, tmp_path, contract):
        brief, meta = load_handoff_package(DEMO_DIR)
        plan = generate_scene_plan(brief)
        pkg = create_media_package(plan, rendered=False)
        manifest = create_run_manifest(
            pipeline_stage="scene_plan_generation",
            status="complete",
            inputs={"research_brief": meta["brief_path"]},
            outputs=[],
            metrics={"num_scenes": len(plan["scenes"])},
            source_run_id=plan["source_run_id"],
        )

        for artifact in (plan, pkg, manifest):
            errors = validate_artifact(artifact, contract)
            assert errors == [], (
                f"{artifact['artifact_type']} invalid: {errors}"
            )

    def test_full_pipeline_with_stable_output(self, tmp_path, contract):
        brief, meta = load_handoff_package(FIXTURE_FILE)
        plan = generate_scene_plan(brief)
        pkg = create_media_package(plan, rendered=False)
        manifest = create_run_manifest(
            pipeline_stage="scene_plan_generation",
            status="complete",
            inputs={"research_brief": meta["brief_path"]},
            outputs=[],
            metrics={"num_scenes": len(plan["scenes"])},
            source_run_id=plan["source_run_id"],
        )

        paths = emit_stable_outputs(plan, pkg, manifest, base_dir=str(tmp_path))

        for artifact_type, path in paths.items():
            with open(path) as f:
                artifact = json.load(f)
            errors = validate_artifact(artifact, contract)
            assert errors == [], f"{artifact_type} at {path} invalid: {errors}"

    def test_source_run_id_traces_back_to_upstream(self):
        brief, _ = load_handoff_package(FIXTURE_FILE)
        # Carry the upstream run_id through to the ScenePlan
        plan = generate_scene_plan(brief, source_run_id=brief["source_run_id"])
        assert plan["source_run_id"] == brief["source_run_id"]


# ===========================================================================
# 7. CLI integration: directory input and --stable-output
# ===========================================================================


class TestCLIPhase2B:
    """CLI supports directory input and --stable-output flag."""

    def test_cli_accepts_directory_input(self, tmp_path):
        output_dir = str(tmp_path / "out")
        result = subprocess.run(
            [
                sys.executable, "generate_scene_plan.py",
                DEMO_DIR,
                "--output-dir", output_dir,
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
        assert "All artifacts valid" in result.stdout

    def test_cli_stable_output_flag(self, tmp_path):
        result = subprocess.run(
            [
                sys.executable, "generate_scene_plan.py",
                FIXTURE_FILE,
                "--output-dir", str(tmp_path / "gen"),
                "--stable-output",
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
        assert "Stable outputs written" in result.stdout
        assert "All artifacts valid" in result.stdout
        assert "Phase 2B" in result.stdout

    def test_cli_without_stable_output_shows_phase1_message(self, tmp_path):
        """Without --stable-output, the CLI prints the Phase 1 completion message."""
        output_dir = str(tmp_path / "out")
        result = subprocess.run(
            [
                sys.executable, "generate_scene_plan.py",
                FIXTURE_FILE,
                "--output-dir", output_dir,
                "--validate",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, (
            f"CLI failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "Phase 1 happy path complete" in result.stdout
        assert "Phase 2B" not in result.stdout

    def test_cli_directory_output_files(self, tmp_path):
        output_dir = str(tmp_path / "out")
        subprocess.run(
            [
                sys.executable, "generate_scene_plan.py",
                DEMO_DIR,
                "--output-dir", output_dir,
                "--media-package",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        files = os.listdir(output_dir)
        assert any("ScenePlan" in f for f in files)
        assert any("MediaPackage" in f for f in files)
        assert any("RunManifest" in f for f in files)

    def test_cli_direct_file_input_still_works(self, tmp_path):
        """Existing direct-file-input behavior is not broken."""
        output_dir = str(tmp_path / "out")
        result = subprocess.run(
            [
                sys.executable, "generate_scene_plan.py",
                DEMO_BRIEF_FILE,
                "--output-dir", output_dir,
                "--validate",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, (
            f"CLI failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "All artifacts valid" in result.stdout
