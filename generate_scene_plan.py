#!/usr/bin/env python3
"""
Phase 1 Happy Path: Generate a ScenePlan from a ResearchBrief.

Usage:
    python generate_scene_plan.py demo_data/jwst_star_formation_early_universe_demo/ResearchBrief.sample.json

Options:
    --output-dir DIR     Directory for output artifacts (default: generated_artifacts/)
    --media-package      Also generate a placeholder MediaPackage
    --validate           Validate all outputs against the shared contract
    --quiet              Suppress progress output
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


def _slug_filename(topic: str, artifact_type: str) -> str:
    """Generate filename per contract: <topic_slug>__<artifact_type>__<timestamp>.json"""
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = topic.replace(" ", "_").lower()
    return f"{slug}__{artifact_type}__{ts}.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a ScenePlan from a ResearchBrief (Phase 1 happy path)"
    )
    parser.add_argument(
        "research_brief",
        help="Path to a ResearchBrief JSON file",
    )
    parser.add_argument(
        "--output-dir",
        default="generated_artifacts",
        help="Directory for output artifacts (default: generated_artifacts/)",
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

    args = parser.parse_args()

    def log(msg: str) -> None:
        if not args.quiet:
            print(msg)

    # --- Load ResearchBrief ---
    log(f"Loading ResearchBrief from: {args.research_brief}")
    try:
        brief = load_research_brief(args.research_brief)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

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

    manifest = create_run_manifest(
        pipeline_stage="scene_plan_generation",
        status="complete",
        inputs={"research_brief": args.research_brief},
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
            pkg = json.load(open(pkg_path))
            pkg_errors = validate_media_package(pkg)
            if pkg_errors:
                print(f"MediaPackage INVALID: {pkg_errors}", file=sys.stderr)
                all_valid = False
            else:
                log("MediaPackage: VALID ✓")

        if not all_valid:
            return 1
        log("\nAll artifacts valid ✓")

    log("\nPhase 1 happy path complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
