#!/usr/bin/env python3
"""
Generate a ScenePlan from a ResearchBrief.

Supports multiple input modes:
  - Direct ResearchBrief JSON file
  - Handoff directory with handoff_manifest.json (auto-detects ResearchBrief)
  - Downloaded orchestration artifact with explicit upstream provenance

Usage:
    # Handoff directory (auto-detects the ResearchBrief via handoff_manifest.json)
    python generate_scene_plan.py demo_data/jwst_star_formation_early_universe_demo/

    # Direct ResearchBrief file (real downstream artifact)
    python generate_scene_plan.py demo_data/jwst_star_formation_early_universe_demo/ResearchBrief.json

    # Canonical fixture from content-research-pipeline
    python generate_scene_plan.py fixtures/research_briefs/jwst_canonical.json

    # Phase 4: orchestration mode — downloaded handoff artifact with explicit run ID
    python generate_scene_plan.py downloaded_handoff/ --upstream-run-id crp-run-abc123

Options:
    --output-dir DIR         Directory for output artifacts (default: generated_artifacts/)
    --stable-output          Write canonical outputs to outputs/<topic_slug>/ (stable, no timestamps)
    --media-package          Also generate a placeholder MediaPackage
    --validate               Validate all outputs against the shared contract
    --quiet                  Suppress progress output
    --upstream-run-id ID     Explicit upstream run ID for provenance (overrides handoff_manifest)
"""

import argparse
import json
import os
import sys

from scene_plan_generator import (
    generate_scene_plan,
    load_research_brief,
    validate_scene_plan,
)
from media_package_writer import (
    create_media_package,
    save_media_package,
    validate_media_package,
)
from run_manifest_writer import (
    create_run_manifest,
    save_run_manifest,
    validate_run_manifest,
)
from research_brief_handoff import (
    load_handoff_package,
    emit_stable_outputs,
)


def _slug_filename(topic: str, artifact_type: str) -> str:
    """Generate filename per contract: <topic_slug>__<artifact_type>__<timestamp>.json"""
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = topic.replace(" ", "_").lower()
    return f"{slug}__{artifact_type}__{ts}.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a ScenePlan from a ResearchBrief (Phase 1 / Phase 2B happy path)"
    )
    parser.add_argument(
        "research_brief",
        help="Path to a ResearchBrief JSON file or a handoff directory containing one",
    )
    parser.add_argument(
        "--output-dir",
        default="generated_artifacts",
        help="Directory for output artifacts (default: generated_artifacts/)",
    )
    parser.add_argument(
        "--stable-output",
        action="store_true",
        help="Also write canonical outputs to outputs/<topic_slug>/ with stable file names",
    )
    parser.add_argument(
        "--media-package",
        action="store_true",
        help="Also generate a placeholder MediaPackage manifest",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate all outputs against the shared contract",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "--upstream-run-id",
        default=None,
        help=(
            "Explicit upstream run ID for provenance tracking. "
            "Overrides the source_run_id from the handoff_manifest.json "
            "when provided (used by orchestration workflows to record "
            "the real Stage 2 run ID)."
        ),
    )

    args = parser.parse_args()

    def log(msg: str) -> None:
        if not args.quiet:
            print(msg)

    # --- Load ResearchBrief (supports file or handoff directory) ---
    log(f"Loading ResearchBrief from: {args.research_brief}")
    try:
        brief, package_meta = load_handoff_package(args.research_brief)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if package_meta["sibling_files"]:
        log(f"Handoff package siblings: {package_meta['sibling_files']}")

    topic = brief["topic"]
    log(f"Topic: {topic}")
    log(f"Research question: {brief.get('research_question', 'N/A')}")

    # --- Generate ScenePlan ---
    log("Generating ScenePlan...")
    scene_plan = generate_scene_plan(brief)
    log(f"Generated {len(scene_plan['scenes'])} scenes")

    # --- Create output directory ---
    os.makedirs(args.output_dir, exist_ok=True)

    # --- Save ScenePlan ---
    plan_filename = _slug_filename(topic, "ScenePlan")
    plan_path = os.path.join(args.output_dir, plan_filename)
    with open(plan_path, "w") as f:
        json.dump(scene_plan, f, indent=2)
    log(f"ScenePlan saved to: {plan_path}")

    # --- Optional: MediaPackage ---
    pkg_path = None
    package = None
    if args.media_package:
        log("Generating placeholder MediaPackage...")
        package = create_media_package(scene_plan, rendered=False)
        pkg_filename = _slug_filename(topic, "MediaPackage")
        pkg_path = os.path.join(args.output_dir, pkg_filename)
        save_media_package(package, pkg_path)
        log(f"MediaPackage saved to: {pkg_path}")

    # --- RunManifest ---
    outputs = [plan_path]
    if pkg_path:
        outputs.append(pkg_path)

    # Build inputs dict — include handoff identity when available
    inputs_dict = {"research_brief": package_meta["brief_path"]}
    if package_meta.get("handoff_manifest"):
        hm = package_meta["handoff_manifest"]
        if hm.get("source_pipeline"):
            inputs_dict["handoff_source_pipeline"] = hm["source_pipeline"]
        if hm.get("source_run_id"):
            inputs_dict["handoff_source_run_id"] = hm["source_run_id"]

    # Explicit upstream run ID overrides the handoff_manifest's source_run_id
    if args.upstream_run_id:
        inputs_dict["handoff_source_run_id"] = args.upstream_run_id

    manifest = create_run_manifest(
        pipeline_stage="scene_plan_generation",
        status="complete",
        inputs=inputs_dict,
        outputs=outputs,
        metrics={
            "num_scenes": len(scene_plan["scenes"]),
            "total_duration_seconds": sum(
                s.get("duration_seconds", 0) for s in scene_plan["scenes"]
            ),
        },
        source_run_id=scene_plan["source_run_id"],
    )
    manifest_filename = _slug_filename(topic, "RunManifest")
    manifest_path = os.path.join(args.output_dir, manifest_filename)
    save_run_manifest(manifest, manifest_path)
    log(f"RunManifest saved to: {manifest_path}")

    # --- Stable canonical outputs ---
    if args.stable_output:
        if package is None:
            package = create_media_package(scene_plan, rendered=False)
        stable_paths = emit_stable_outputs(scene_plan, package, manifest)
        log(f"Stable outputs written to: {os.path.dirname(stable_paths['ScenePlan'])}")
        for artifact_type, path in stable_paths.items():
            log(f"  {artifact_type}: {path}")

    # --- Validation ---
    if args.validate:
        log("\n--- Validation ---")
        all_valid = True

        plan_errors = validate_scene_plan(scene_plan)
        if plan_errors:
            print(f"ScenePlan INVALID: {plan_errors}", file=sys.stderr)
            all_valid = False
        else:
            log("ScenePlan: VALID ✓")

        manifest_errors = validate_run_manifest(manifest)
        if manifest_errors:
            print(f"RunManifest INVALID: {manifest_errors}", file=sys.stderr)
            all_valid = False
        else:
            log("RunManifest: VALID ✓")

        if args.media_package:
            with open(pkg_path) as _f:
                pkg = json.load(_f)
            pkg_errors = validate_media_package(pkg)
            if pkg_errors:
                print(f"MediaPackage INVALID: {pkg_errors}", file=sys.stderr)
                all_valid = False
            else:
                log("MediaPackage: VALID ✓")

        if not all_valid:
            return 1
        log("\nAll artifacts valid ✓")

    if args.stable_output:
        log("\nPhase 2B happy path complete.")
    else:
        log("\nPhase 1 happy path complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
