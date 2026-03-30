"""
Media Package writer for the Media Generation Pipeline.

Produces a contract-valid placeholder MediaPackage artifact.
In Phase 1, full rendering may not be stable, so this creates a
lightweight manifest describing the expected media outputs.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "1.0.0"
PRODUCER = "media-generation-pipeline"

MEDIA_PACKAGE_REQUIRED_FIELDS = [
    "artifact_type", "schema_version", "artifact_id", "created_at",
    "producer", "source_run_id", "topic", "media_type",
    "assets", "render_manifest", "attribution",
]

ASSET_REQUIRED_FIELDS = [
    "asset_id", "asset_type", "title", "local_path", "mime_type",
    "duration_seconds", "resolution", "source_scene_id", "metadata",
]


def create_media_package(
    scene_plan: Dict[str, Any],
    media_type: str = "video/mp4",
    rendered: bool = False,
    source_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a contract-valid MediaPackage from a ScenePlan.

    When rendered=False (default), this creates a placeholder manifest
    listing expected assets without actual files. When rendered=True,
    it assumes assets exist at the paths described.

    Args:
        scene_plan: A validated ScenePlan dict.
        media_type: MIME type of the primary output.
        rendered: Whether assets have actually been rendered.
        source_run_id: Run ID linking back to the pipeline run.

    Returns:
        A contract-valid MediaPackage dict.
    """
    topic = scene_plan.get("topic", "unknown")
    run_id = source_run_id or scene_plan.get("source_run_id", f"run-{uuid.uuid4().hex[:12]}")
    scenes = scene_plan.get("scenes", [])

    assets = _build_asset_list(scenes, rendered)

    status = "rendered" if rendered else "placeholder"

    package: Dict[str, Any] = {
        "artifact_type": "MediaPackage",
        "schema_version": SCHEMA_VERSION,
        "artifact_id": f"media-pkg-{uuid.uuid4().hex[:8]}",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "producer": PRODUCER,
        "source_run_id": run_id,
        "topic": topic,
        "media_type": media_type,
        "assets": assets,
        "render_manifest": {
            "status": status,
            "scene_plan_id": scene_plan.get("artifact_id", ""),
            "total_scenes": len(scenes),
            "total_duration_seconds": sum(
                s.get("duration_seconds", 0) for s in scenes
            ),
        },
        "attribution": _build_attribution(scene_plan),
    }

    return package


def _build_asset_list(
    scenes: List[Dict[str, Any]], rendered: bool
) -> List[Dict[str, Any]]:
    """Build asset entries from scene list."""
    assets: List[Dict[str, Any]] = []

    for scene in scenes:
        scene_id = scene.get("scene_id", "unknown")

        # Image asset for each scene
        assets.append({
            "asset_id": f"img-{scene_id}",
            "asset_type": "image",
            "title": f"Visual for {scene.get('title', scene_id)}",
            "local_path": f"generated_content/images/{scene_id}.png"
                          if rendered else f"(placeholder) images/{scene_id}.png",
            "mime_type": "image/png",
            "duration_seconds": scene.get("duration_seconds", 0),
            "resolution": "1024x1024",
            "source_scene_id": scene_id,
            "metadata": {"rendered": rendered},
        })

        # Audio asset for each scene
        assets.append({
            "asset_id": f"audio-{scene_id}",
            "asset_type": "audio",
            "title": f"Narration for {scene.get('title', scene_id)}",
            "local_path": f"generated_content/audio/{scene_id}.mp3"
                          if rendered else f"(placeholder) audio/{scene_id}.mp3",
            "mime_type": "audio/mpeg",
            "duration_seconds": scene.get("duration_seconds", 0),
            "resolution": "",
            "source_scene_id": scene_id,
            "metadata": {"rendered": rendered},
        })

    # Final assembled video
    total_duration = sum(s.get("duration_seconds", 0) for s in scenes)
    assets.append({
        "asset_id": "final-video",
        "asset_type": "video",
        "title": "Final assembled video",
        "local_path": "generated_content/final_video.mp4"
                      if rendered else "(placeholder) final_video.mp4",
        "mime_type": "video/mp4",
        "duration_seconds": total_duration,
        "resolution": "1920x1080",
        "source_scene_id": "",
        "metadata": {"rendered": rendered},
    })

    return assets


def _build_attribution(scene_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Build attribution metadata."""
    return {
        "producer": PRODUCER,
        "scene_plan_id": scene_plan.get("artifact_id", ""),
        "topic": scene_plan.get("topic", ""),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def validate_media_package(package: Dict[str, Any]) -> List[str]:
    """Validate a MediaPackage against the shared contract."""
    errors: List[str] = []

    for field in MEDIA_PACKAGE_REQUIRED_FIELDS:
        if field not in package:
            errors.append(f"Missing required field: {field}")

    if package.get("artifact_type") != "MediaPackage":
        errors.append(
            f"artifact_type must be 'MediaPackage', got '{package.get('artifact_type')}'"
        )

    assets = package.get("assets", [])
    if not isinstance(assets, list):
        errors.append("'assets' must be a list")
        return errors

    for i, asset in enumerate(assets):
        for field in ASSET_REQUIRED_FIELDS:
            if field not in asset:
                errors.append(f"Asset {i}: missing required field '{field}'")

    return errors


def save_media_package(package: Dict[str, Any], path: str) -> str:
    """Write a MediaPackage to a JSON file."""
    with open(path, "w") as f:
        json.dump(package, f, indent=2)
    return path
