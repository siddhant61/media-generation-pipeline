#!/usr/bin/env python3
"""
Artifact Validator for the Media Generation Pipeline.

Validates JSON artifacts against the shared contract defined in
contracts/shared_artifacts.json.

Usage:
    python validate_artifacts.py path/to/artifact.json
    python validate_artifacts.py generated_artifacts/    # validate all .json files
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List


def load_contract(contract_path: str = None) -> Dict[str, Any]:
    """Load the shared artifact contract."""
    if contract_path is None:
        contract_path = os.path.join(
            os.path.dirname(__file__), "contracts", "shared_artifacts.json"
        )
    with open(contract_path, "r") as f:
        return json.load(f)


def validate_artifact(artifact: Dict[str, Any], contract: Dict[str, Any]) -> List[str]:
    """
    Validate an artifact against the shared contract.

    Returns a list of error messages. Empty list means valid.
    """
    errors: List[str] = []

    artifact_type = artifact.get("artifact_type")
    if not artifact_type:
        errors.append("Missing 'artifact_type' field")
        return errors

    artifacts_spec = contract.get("artifacts", {})
    if artifact_type not in artifacts_spec:
        errors.append(f"Unknown artifact_type: '{artifact_type}'")
        return errors

    spec = artifacts_spec[artifact_type]

    # Check top-level required fields
    for field in spec.get("required_fields", []):
        if field not in artifact:
            errors.append(f"Missing required field: '{field}'")

    # Check nested required fields for known item types
    nested_checks = {
        "scenes": "scene_required_fields",
        "sources": "source_item_required_fields",
        "documents": "document_required_fields",
        "chunks": "chunk_required_fields",
        "nodes": "node_required_fields",
        "edges": "edge_required_fields",
        "assets": "asset_required_fields",
    }

    for list_field, spec_key in nested_checks.items():
        if spec_key in spec and list_field in artifact:
            items = artifact[list_field]
            if isinstance(items, list):
                required = spec[spec_key]
                for i, item in enumerate(items):
                    if isinstance(item, dict):
                        for req_field in required:
                            if req_field not in item:
                                errors.append(
                                    f"{list_field}[{i}]: missing required field '{req_field}'"
                                )

    return errors


def validate_file(path: str, contract: Dict[str, Any]) -> List[str]:
    """Validate a single JSON artifact file."""
    try:
        with open(path, "r") as f:
            artifact = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except FileNotFoundError:
        return [f"File not found: {path}"]

    return validate_artifact(artifact, contract)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate artifacts against the shared contract"
    )
    parser.add_argument(
        "path",
        help="Path to a JSON artifact file or directory of artifacts",
    )
    parser.add_argument(
        "--contract",
        default=None,
        help="Path to shared_artifacts.json (default: contracts/shared_artifacts.json)",
    )

    args = parser.parse_args()
    contract = load_contract(args.contract)

    paths: List[str] = []
    if os.path.isdir(args.path):
        for fname in sorted(os.listdir(args.path)):
            if fname.endswith(".json"):
                paths.append(os.path.join(args.path, fname))
    else:
        paths.append(args.path)

    if not paths:
        print("No JSON files found.", file=sys.stderr)
        return 1

    all_valid = True
    for p in paths:
        errors = validate_file(p, contract)
        basename = os.path.basename(p)
        if errors:
            print(f"INVALID {basename}:")
            for e in errors:
                print(f"  - {e}")
            all_valid = False
        else:
            print(f"VALID   {basename} ✓")

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
