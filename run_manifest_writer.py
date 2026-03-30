"""
Run Manifest writer for the Media Generation Pipeline.

Produces a contract-valid RunManifest artifact tracking pipeline execution.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "1.0.0"
PRODUCER = "media-generation-pipeline"

RUN_MANIFEST_REQUIRED_FIELDS = [
    "artifact_type", "schema_version", "artifact_id", "created_at",
    "producer", "source_run_id", "pipeline_name", "pipeline_stage",
    "status", "inputs", "outputs", "metrics", "errors",
]


def create_run_manifest(
    pipeline_stage: str,
    status: str,
    inputs: Dict[str, Any],
    outputs: Optional[List[str]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    errors: Optional[List[str]] = None,
    source_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a contract-valid RunManifest.

    Args:
        pipeline_stage: Current pipeline stage (e.g. 'scene_plan_generation').
        status: Run status ('pending', 'running', 'complete', 'failed').
        inputs: Dict of input references.
        outputs: List of output artifact paths/IDs.
        metrics: Dict of run metrics.
        errors: List of error messages.
        source_run_id: Run ID (auto-generated if not provided).

    Returns:
        A contract-valid RunManifest dict.
    """
    run_id = source_run_id or f"run-{uuid.uuid4().hex[:12]}"

    manifest: Dict[str, Any] = {
        "artifact_type": "RunManifest",
        "schema_version": SCHEMA_VERSION,
        "artifact_id": f"manifest-{uuid.uuid4().hex[:8]}",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "producer": PRODUCER,
        "source_run_id": run_id,
        "pipeline_name": "media-generation-pipeline",
        "pipeline_stage": pipeline_stage,
        "status": status,
        "inputs": inputs,
        "outputs": outputs or [],
        "metrics": metrics or {},
        "errors": errors or [],
    }

    return manifest


def validate_run_manifest(manifest: Dict[str, Any]) -> List[str]:
    """Validate a RunManifest against the shared contract."""
    errors: List[str] = []
    for field in RUN_MANIFEST_REQUIRED_FIELDS:
        if field not in manifest:
            errors.append(f"Missing required field: {field}")
    if manifest.get("artifact_type") != "RunManifest":
        errors.append(
            f"artifact_type must be 'RunManifest', got '{manifest.get('artifact_type')}'"
        )
    return errors


def save_run_manifest(manifest: Dict[str, Any], path: str) -> str:
    """Write a RunManifest to a JSON file."""
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return path
