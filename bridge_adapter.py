"""
Bridge Adapter: contract ScenePlan → legacy rendering pipeline.

Maps contract-compliant ScenePlan scenes to the legacy Scene dataclass
used by SceneManager, ContentGenerator, ImageProcessor, and VideoAssembler.
Also provides utilities for attempting a render pass and emitting a
contract-valid MediaPackage with rich render metadata.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from scene_manager import Scene
from media_package_writer import create_media_package


def scene_plan_to_legacy_scenes(scene_plan: Dict[str, Any]) -> List[Scene]:
    """
    Convert contract ScenePlan scenes to legacy Scene dataclass instances.

    Mapping:
        scene_id    → Scene.id
        title       → Scene.name
        visual_brief → Scene.prompt
        narration   → Scene.narration
        (image_file, audio_file default to empty — not yet rendered)

    Args:
        scene_plan: A validated ScenePlan dict with a ``scenes`` list.

    Returns:
        List of legacy Scene dataclass instances.

    Raises:
        ValueError: If scene_plan has no ``scenes`` key or scenes is empty.
    """
    scenes_data = scene_plan.get("scenes")
    if not scenes_data or not isinstance(scenes_data, list):
        raise ValueError("ScenePlan must contain a non-empty 'scenes' list")

    legacy_scenes: List[Scene] = []
    for sc in scenes_data:
        legacy_scenes.append(Scene(
            id=sc.get("scene_id", f"scene-{len(legacy_scenes)+1:03d}"),
            name=sc.get("title", "Untitled"),
            prompt=sc.get("visual_brief", ""),
            narration=sc.get("narration", ""),
            image_file="",
            audio_file="",
        ))

    return legacy_scenes


def legacy_scene_to_contract_dict(legacy_scene: Scene) -> Dict[str, Any]:
    """
    Reverse-map a legacy Scene back to a partial contract scene dict.

    This is useful for round-trip validation and for enriching a
    MediaPackage with render results (e.g. populated image_file / audio_file).
    """
    return {
        "scene_id": legacy_scene.id,
        "title": legacy_scene.name,
        "visual_brief": legacy_scene.prompt,
        "narration": legacy_scene.narration,
        "image_file": legacy_scene.image_file,
        "audio_file": legacy_scene.audio_file,
    }


def attempt_render(
    legacy_scenes: List[Scene],
    output_dir: str = "generated_content",
) -> Dict[str, Any]:
    """
    Attempt to render legacy scenes through the full pipeline.

    This tries to import and initialise the legacy ContentGenerator,
    ImageProcessor, and VideoAssembler.  Because those require live
    API keys (OpenAI + Stability AI), this will likely fail in CI or
    local environments without keys.  The function captures exactly
    where the failure occurs so callers can emit a rich MediaPackage
    placeholder.

    Returns a dict with:
        success (bool):      Whether the full render completed.
        stage (str):         Last stage attempted.
        error (str | None):  Error message if failed.
        rendered_scenes (List[Scene]):  Scenes (possibly with image/audio populated).
        output_dir (str):    Output directory used.
        video_path (str):    Path to final video (empty string if not rendered).
    """
    result: Dict[str, Any] = {
        "success": False,
        "stage": "init",
        "error": None,
        "rendered_scenes": legacy_scenes,
        "output_dir": output_dir,
        "video_path": "",
    }

    os.makedirs(output_dir, exist_ok=True)

    # --- Stage 1: Initialise ContentGenerator ---
    try:
        result["stage"] = "content_generator_init"
        from config import APIConfig
        api_config = APIConfig()
        api_config.output_dir = output_dir
        api_config.validate()  # raises if keys missing
    except (ValueError, ImportError) as exc:
        result["error"] = f"API configuration failed: {exc}"
        return result

    try:
        from content_generator import ContentGenerator
        content_gen = ContentGenerator(api_config)
    except Exception as exc:
        result["error"] = f"ContentGenerator init failed: {exc}"
        return result

    # --- Stage 2: Generate content for each scene ---
    try:
        result["stage"] = "content_generation"
        for scene in legacy_scenes:
            gen_result = content_gen.generate_scene_content(scene)
            scene.narration = gen_result.get("narration", scene.narration)
            scene.image_file = gen_result.get("image_file", "")
    except Exception as exc:
        result["error"] = f"Content generation failed: {exc}"
        return result

    # --- Stage 3: Generate audio ---
    try:
        result["stage"] = "audio_generation"
        for scene in legacy_scenes:
            if scene.narration:
                audio_path = content_gen.generate_audio(scene.narration, scene.id)
                scene.audio_file = audio_path
    except Exception as exc:
        result["error"] = f"Audio generation failed: {exc}"
        return result

    # --- Stage 4: Assemble video ---
    try:
        result["stage"] = "video_assembly"
        from video_assembler import VideoAssembler
        assembler = VideoAssembler(api_config)
        video_path = assembler.create_video_from_scenes(legacy_scenes)
        result["video_path"] = video_path
    except Exception as exc:
        result["error"] = f"Video assembly failed: {exc}"
        return result

    result["success"] = True
    result["stage"] = "complete"
    result["rendered_scenes"] = legacy_scenes
    return result


def create_bridged_media_package(
    scene_plan: Dict[str, Any],
    render_result: Dict[str, Any],
    source_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a contract-valid MediaPackage enriched with bridge render metadata.

    If rendering succeeded, assets point to real files and status is
    ``"rendered"``.  If rendering failed, the package is a rich placeholder
    that records exactly where the pipeline broke.

    Args:
        scene_plan: The contract ScenePlan that was bridged.
        render_result: The dict returned by :func:`attempt_render`.
        source_run_id: Optional run ID override.

    Returns:
        A contract-valid MediaPackage dict.
    """
    rendered = render_result.get("success", False)

    # Start from the standard writer
    package = create_media_package(
        scene_plan,
        rendered=rendered,
        source_run_id=source_run_id,
    )

    # Enrich render_manifest with bridge metadata
    package["render_manifest"]["bridge"] = {
        "adapter": "bridge_adapter.scene_plan_to_legacy_scenes",
        "last_stage": render_result.get("stage", "unknown"),
        "success": rendered,
        "error": render_result.get("error"),
        "video_path": render_result.get("video_path", ""),
        "output_dir": render_result.get("output_dir", ""),
    }

    # If rendered, update asset paths from actual results
    if rendered:
        rendered_scenes = render_result.get("rendered_scenes", [])
        for scene in rendered_scenes:
            for asset in package["assets"]:
                if asset.get("source_scene_id") == scene.id:
                    if asset["asset_type"] == "image" and scene.image_file:
                        asset["local_path"] = scene.image_file
                    elif asset["asset_type"] == "audio" and scene.audio_file:
                        asset["local_path"] = scene.audio_file
        # Update video asset
        video_path = render_result.get("video_path", "")
        if video_path:
            for asset in package["assets"]:
                if asset["asset_type"] == "video":
                    asset["local_path"] = video_path

    return package
