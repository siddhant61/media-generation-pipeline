"""
Phase 2B / Phase 3: ResearchBrief Handoff Package loader and stable output emitter.

Provides utilities for consuming the canonical ResearchBrief artifact emitted
by content-research-pipeline, whether delivered as:
  - a bare ResearchBrief JSON file
  - a handoff directory containing a ResearchBrief plus a RunManifest and
    other artifacts (the format content-research-pipeline writes)
  - a handoff directory containing a ``handoff_manifest.json`` that declares
    the primary artifact and the full list of artifacts in the package
    (Phase 3 canonical downstream handoff format)

Also provides a helper to write ScenePlan / MediaPackage / RunManifest to
the stable canonical output location:
  outputs/<topic_slug>/ScenePlan.json
  outputs/<topic_slug>/MediaPackage.json
  outputs/<topic_slug>/RunManifest.json
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from scene_plan_generator import load_research_brief, RESEARCH_BRIEF_REQUIRED_FIELDS


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Top-level directory for stable canonical outputs (no timestamps).
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")

#: File names used inside a per-topic output directory.
STABLE_SCENE_PLAN_FILE = "ScenePlan.json"
STABLE_MEDIA_PACKAGE_FILE = "MediaPackage.json"
STABLE_RUN_MANIFEST_FILE = "RunManifest.json"

#: Canonical handoff manifest filename emitted by content-research-pipeline.
HANDOFF_MANIFEST_FILE = "handoff_manifest.json"


# ---------------------------------------------------------------------------
# Handoff manifest loading
# ---------------------------------------------------------------------------


def load_handoff_manifest(directory: str) -> Optional[Dict[str, Any]]:
    """Load ``handoff_manifest.json`` from a handoff directory, if present.

    The handoff manifest is a lightweight package index emitted by
    ``content-research-pipeline`` alongside the primary artifact.  It
    declares which file is the ``primary_artifact`` and lists all artifacts
    included in the handoff package.

    Args:
        directory: Path to a directory that may contain a handoff manifest.

    Returns:
        The parsed manifest dict, or ``None`` if no
        ``handoff_manifest.json`` file exists in the directory.

    Raises:
        ValueError: If ``handoff_manifest.json`` exists but cannot be
            parsed as valid JSON.
    """
    manifest_path = os.path.join(directory, HANDOFF_MANIFEST_FILE)
    if not os.path.isfile(manifest_path):
        return None
    try:
        with open(manifest_path) as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {manifest_path}: {exc}"
        ) from exc


def find_research_brief_in_dir(directory: str) -> str:
    """Locate the ResearchBrief JSON file inside a handoff directory.

    Search order:

    1. **``handoff_manifest.json``** — if present, read ``primary_artifact``
       and resolve to an absolute path.  This is the canonical Phase 3
       format emitted by ``content-research-pipeline``.
    2. **Filename pattern** — files ending with or containing
       ``ResearchBrief`` (case-insensitive).
    3. **Content inspection** — scan JSON files for
       ``artifact_type == "ResearchBrief"``.

    Args:
        directory: Path to a directory produced by content-research-pipeline.

    Returns:
        Absolute path to the ResearchBrief JSON file.

    Raises:
        FileNotFoundError: If no ResearchBrief file can be found, or if the
            primary artifact declared in the handoff manifest does not exist.
        ValueError: If multiple ambiguous candidates are found.
    """
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Not a directory: {directory}")

    # Priority 0 — canonical Phase 3 handoff_manifest.json
    handoff_manifest = load_handoff_manifest(directory)
    if handoff_manifest is not None:
        primary = handoff_manifest.get("primary_artifact")
        if primary:
            primary_path = os.path.join(directory, primary)
            if not os.path.isfile(primary_path):
                raise FileNotFoundError(
                    f"handoff_manifest.json declares primary_artifact "
                    f"'{primary}' but that file does not exist in {directory}"
                )
            return primary_path

    json_files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.endswith(".json") and f != HANDOFF_MANIFEST_FILE
    ]

    # Priority 1 — exact naming conventions used by content-research-pipeline
    priority = [
        p for p in json_files
        if os.path.basename(p).lower().startswith("researchbrief")
        or "researchbrief" in os.path.basename(p).lower()
    ]
    if len(priority) == 1:
        return priority[0]
    if len(priority) > 1:
        # Prefer the shortest filename (e.g., ResearchBrief.json over ResearchBrief.sample.json)
        priority.sort(key=lambda p: len(os.path.basename(p)))
        return priority[0]

    # Priority 2 — inspect artifact_type field
    candidates = []
    for path in json_files:
        try:
            with open(path) as f:
                data = json.load(f)
            if data.get("artifact_type") == "ResearchBrief":
                candidates.append(path)
        except (json.JSONDecodeError, OSError):
            continue

    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise ValueError(
            f"Multiple ResearchBrief files found in {directory}: {candidates}"
        )

    raise FileNotFoundError(
        f"No ResearchBrief JSON file found in directory: {directory}"
    )


def load_handoff_package(path: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load a ResearchBrief from either a handoff directory or a direct JSON file.

    This is the primary entry point for consuming the canonical upstream
    artifact emitted by content-research-pipeline.

    Accepted inputs:
        - A path to a ResearchBrief JSON file.
        - A path to a handoff directory that contains a ResearchBrief JSON
          file (with optional sibling RunManifest, sources/, etc.).
        - A path to a handoff directory that contains a ``handoff_manifest.json``
          (canonical Phase 3 format from content-research-pipeline).

    When a ``handoff_manifest.json`` is present the ``package_meta`` dict
    includes its contents under the ``"handoff_manifest"`` key, giving
    callers access to the full package index including ``source_run_id``,
    ``topic``, and the declared artifact list.

    Args:
        path: Path to a ResearchBrief JSON file or a handoff directory.

    Returns:
        A tuple ``(brief, package_meta)`` where:
          - ``brief`` is a validated ResearchBrief dict.
          - ``package_meta`` is a dict describing the handoff package::

              {
                "source_path": str,
                "brief_path": str,
                "sibling_files": List[str],
                "handoff_manifest": Dict | None,  # Phase 3: manifest contents
              }

    Raises:
        FileNotFoundError: If the path does not exist or no ResearchBrief
            can be found in the given directory.
        ValueError: If the loaded artifact is not a valid ResearchBrief.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: {path}")

    handoff_manifest: Optional[Dict[str, Any]] = None

    if os.path.isdir(path):
        handoff_manifest = load_handoff_manifest(path)
        brief_path = find_research_brief_in_dir(path)
        sibling_files = [
            f for f in os.listdir(path)
            if f.endswith(".json")
            and os.path.join(path, f) != brief_path
            and f != HANDOFF_MANIFEST_FILE
        ]
    else:
        brief_path = path
        sibling_files = []

    brief = load_research_brief(brief_path)

    package_meta: Dict[str, Any] = {
        "source_path": path,
        "brief_path": brief_path,
        "sibling_files": sorted(sibling_files),
        "handoff_manifest": handoff_manifest,
    }

    return brief, package_meta


# ---------------------------------------------------------------------------
# Stable output location
# ---------------------------------------------------------------------------


def _topic_slug(topic: str) -> str:
    """Return a filesystem-safe slug for a topic string.

    Replaces spaces and any character that is not alphanumeric, hyphen,
    or underscore with an underscore, then lowercases the result.
    """
    import re
    slug = topic.lower()
    slug = re.sub(r"[^\w\-]", "_", slug)
    slug = re.sub(r"_+", "_", slug)
    return slug.strip("_")


def stable_output_dir(topic: str, base_dir: Optional[str] = None) -> str:
    """Return the stable output directory path for a given topic.

    The directory is ``<base_dir>/<topic_slug>/`` and is created if it does
    not already exist.

    Args:
        topic: The artifact ``topic`` field (e.g.
            ``"jwst_star_formation_early_universe_demo"``).
        base_dir: Override for the top-level outputs directory.  Defaults to
            ``outputs/`` relative to this file.

    Returns:
        Absolute path to the per-topic output directory.
    """
    root = base_dir if base_dir is not None else OUTPUTS_DIR
    out_dir = os.path.join(root, _topic_slug(topic))
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def emit_stable_outputs(
    scene_plan: Dict[str, Any],
    media_package: Dict[str, Any],
    run_manifest: Dict[str, Any],
    base_dir: Optional[str] = None,
) -> Dict[str, str]:
    """Write ScenePlan, MediaPackage, and RunManifest to the stable output location.

    Outputs are written to ``outputs/<topic_slug>/`` with fixed file names
    (no timestamps), making them easy to reference in documentation and tests.
    Each run overwrites the previous outputs for the same topic.

    Args:
        scene_plan: A contract-valid ScenePlan dict.
        media_package: A contract-valid MediaPackage dict.
        run_manifest: A contract-valid RunManifest dict.
        base_dir: Override for the top-level outputs directory.

    Returns:
        Dict mapping artifact type to the absolute path where it was written::

            {
                "ScenePlan": "/abs/path/outputs/topic_slug/ScenePlan.json",
                "MediaPackage": "/abs/path/outputs/topic_slug/MediaPackage.json",
                "RunManifest": "/abs/path/outputs/topic_slug/RunManifest.json",
            }
    """
    topic = scene_plan.get("topic", "unknown")
    out_dir = stable_output_dir(topic, base_dir=base_dir)

    paths: Dict[str, str] = {}

    for artifact, filename in [
        (scene_plan, STABLE_SCENE_PLAN_FILE),
        (media_package, STABLE_MEDIA_PACKAGE_FILE),
        (run_manifest, STABLE_RUN_MANIFEST_FILE),
    ]:
        artifact_type = artifact.get("artifact_type", filename.replace(".json", ""))
        out_path = os.path.join(out_dir, filename)
        with open(out_path, "w") as f:
            json.dump(artifact, f, indent=2)
        paths[artifact_type] = out_path

    return paths


def list_stable_outputs(topic: str, base_dir: Optional[str] = None) -> Dict[str, str]:
    """Return paths of stable output files for a topic, if they exist.

    Args:
        topic: The artifact ``topic`` field.
        base_dir: Override for the top-level outputs directory.

    Returns:
        Dict mapping artifact type to path, for each file that exists.
    """
    root = base_dir if base_dir is not None else OUTPUTS_DIR
    out_dir = os.path.join(root, _topic_slug(topic))

    result: Dict[str, str] = {}
    for artifact_type, filename in [
        ("ScenePlan", STABLE_SCENE_PLAN_FILE),
        ("MediaPackage", STABLE_MEDIA_PACKAGE_FILE),
        ("RunManifest", STABLE_RUN_MANIFEST_FILE),
    ]:
        candidate = os.path.join(out_dir, filename)
        if os.path.isfile(candidate):
            result[artifact_type] = candidate
    return result
