#!/usr/bin/env python3
"""
Phase 1.5 Bridge CLI: route a ResearchBrief or ScenePlan through the
contract-aligned ScenePlan path *and* the legacy rendering pipeline.

Usage:
    # From a ResearchBrief (generates ScenePlan first, then bridges)
    python bridge_cli.py demo_data/jwst_star_formation_early_universe_demo/ResearchBrief.sample.json

    # From an existing ScenePlan
    python bridge_cli.py generated_artifacts/my__ScenePlan__20260330.json --scene-plan

    # Dry-run (bridge + validate, skip rendering)
    python bridge_cli.py ResearchBrief.sample.json --dry-run --validate

    # Full render attempt
    python bridge_cli.py ResearchBrief.sample.json --render --validate
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
from media_package_writer import save_media_package, validate_media_package
from run_manifest_writer import create_run_manifest, save_run_manifest
from bridge_adapter import (
    scene_plan_to_legacy_scenes,
    attempt_render,
    create_bridged_media_package,
)


def _slug_filename(topic: str, artifact_type: str) -> str:
    """Generate filename per contract naming convention."""
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = topic.replace(" ", "_").lower()
    return f"{slug}__{artifact_type}__{ts}.json"


def _load_scene_plan(path: str) -> dict:
    """Load and minimally validate a ScenePlan JSON file."""
    with open(path, "r") as f:
        plan = json.load(f)
    if plan.get("artifact_type") != "ScenePlan":
        raise ValueError(
            f"Expected artifact_type 'ScenePlan', got '{plan.get('artifact_type')}'"
        )
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 1.5 Bridge: ResearchBrief/ScenePlan → legacy render pipeline"
    )
    parser.add_argument(
        "input_file",
        help="Path to a ResearchBrief or ScenePlan JSON file",
    )
    parser.add_argument(
        "--scene-plan",
        action="store_true",
        help="Treat input as a ScenePlan (default: treat as ResearchBrief)",
    )
    parser.add_argument(
        "--output-dir",
        default="generated_artifacts",
        help="Directory for output artifacts (default: generated_artifacts/)",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Attempt full rendering through the legacy pipeline (requires API keys)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Bridge and validate only, do not attempt rendering",
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

    # --- Load input ---
    if args.scene_plan:
        log(f"Loading ScenePlan from: {args.input_file}")
        try:
            scene_plan = _load_scene_plan(args.input_file)
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    else:
        log(f"Loading ResearchBrief from: {args.input_file}")
        try:
            brief = load_research_brief(args.input_file)
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        log(f"Topic: {brief['topic']}")
        log("Generating ScenePlan...")
        scene_plan = generate_scene_plan(brief)
        log(f"Generated {len(scene_plan['scenes'])} scenes")

    topic = scene_plan.get("topic", "unknown")

    # --- Validate ScenePlan ---
    plan_errors = validate_scene_plan(scene_plan)
    if plan_errors:
        print(f"ScenePlan INVALID: {plan_errors}", file=sys.stderr)
        return 1
    log("ScenePlan: VALID ✓")

    # --- Bridge to legacy Scene dataclass ---
    log("Bridging ScenePlan scenes to legacy Scene format...")
    legacy_scenes = scene_plan_to_legacy_scenes(scene_plan)
    log(f"Bridged {len(legacy_scenes)} scenes:")
    for sc in legacy_scenes:
        log(f"  {sc.id}: {sc.name}")

    # --- Create output directory ---
    os.makedirs(args.output_dir, exist_ok=True)

    # --- Save ScenePlan ---
    plan_filename = _slug_filename(topic, "ScenePlan")
    plan_path = os.path.join(args.output_dir, plan_filename)
    with open(plan_path, "w") as f:
        json.dump(scene_plan, f, indent=2)
    log(f"ScenePlan saved to: {plan_path}")

    # --- Render or dry-run ---
    if args.dry_run or not args.render:
        log("\nDry-run mode — skipping rendering.")
        render_result = {
            "success": False,
            "stage": "skipped",
            "error": "Rendering skipped (dry-run mode)",
            "rendered_scenes": legacy_scenes,
            "output_dir": args.output_dir,
            "video_path": "",
        }
    else:
        log("\nAttempting full render through legacy pipeline...")
        render_result = attempt_render(legacy_scenes, output_dir=args.output_dir)
        if render_result["success"]:
            log("✅ Rendering completed successfully!")
            log(f"   Video: {render_result['video_path']}")
        else:
            log(f"⚠️  Rendering stopped at stage: {render_result['stage']}")
            log(f"   Error: {render_result['error']}")

    # --- Emit bridged MediaPackage ---
    log("\nGenerating bridged MediaPackage...")
    package = create_bridged_media_package(
        scene_plan, render_result, source_run_id=scene_plan.get("source_run_id")
    )
    pkg_filename = _slug_filename(topic, "MediaPackage")
    pkg_path = os.path.join(args.output_dir, pkg_filename)
    save_media_package(package, pkg_path)
    log(f"MediaPackage saved to: {pkg_path}")

    # --- RunManifest ---
    outputs = [plan_path, pkg_path]
    stage = "bridge_render" if args.render else "bridge_dry_run"
    status = "complete" if render_result["success"] else "partial"

    manifest = create_run_manifest(
        pipeline_stage=stage,
        status=status,
        inputs={"input_file": args.input_file, "input_type": "ScenePlan" if args.scene_plan else "ResearchBrief"},
        outputs=outputs,
        metrics={
            "num_scenes": len(scene_plan["scenes"]),
            "total_duration_seconds": sum(
                s.get("duration_seconds", 0) for s in scene_plan["scenes"]
            ),
            "render_attempted": args.render,
            "render_success": render_result["success"],
            "render_last_stage": render_result["stage"],
        },
        errors=[render_result["error"]] if render_result.get("error") else [],
        source_run_id=scene_plan.get("source_run_id"),
    )
    manifest_filename = _slug_filename(topic, "RunManifest")
    manifest_path = os.path.join(args.output_dir, manifest_filename)
    save_run_manifest(manifest, manifest_path)
    log(f"RunManifest saved to: {manifest_path}")

    # --- Validation ---
    if args.validate:
        log("\n--- Validation ---")
        all_valid = True

        plan_errs = validate_scene_plan(scene_plan)
        if plan_errs:
            print(f"ScenePlan INVALID: {plan_errs}", file=sys.stderr)
            all_valid = False
        else:
            log("ScenePlan: VALID ✓")

        pkg_errs = validate_media_package(package)
        if pkg_errs:
            print(f"MediaPackage INVALID: {pkg_errs}", file=sys.stderr)
            all_valid = False
        else:
            log("MediaPackage: VALID ✓")

        from run_manifest_writer import validate_run_manifest
        manifest_errs = validate_run_manifest(manifest)
        if manifest_errs:
            print(f"RunManifest INVALID: {manifest_errs}", file=sys.stderr)
            all_valid = False
        else:
            log("RunManifest: VALID ✓")

        if not all_valid:
            return 1
        log("\nAll artifacts valid ✓")

    # --- Summary ---
    log(f"\n{'='*50}")
    log("Phase 1.5 Bridge Summary")
    log(f"{'='*50}")
    log(f"  Input:           {args.input_file}")
    log(f"  Scenes bridged:  {len(legacy_scenes)}")
    log(f"  Render attempted: {args.render}")
    log(f"  Render success:  {render_result['success']}")
    if render_result.get("error"):
        log(f"  Render blocked:  {render_result['stage']} — {render_result['error']}")
    log(f"  Artifacts dir:   {args.output_dir}")
    log(f"{'='*50}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
