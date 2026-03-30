"""
Scene Plan Generator for the Media Generation Pipeline.

Consumes a ResearchBrief artifact and produces a contract-valid ScenePlan artifact.
This is the core Phase 1 happy path for this repository.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "1.0.0"
PRODUCER = "media-generation-pipeline"

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "research_briefs")

SCENE_PLAN_REQUIRED_FIELDS = [
    "artifact_type", "schema_version", "artifact_id", "created_at",
    "producer", "source_run_id", "topic", "narrative_goal",
    "target_audience", "style_profile", "scenes",
]

SCENE_REQUIRED_FIELDS = [
    "scene_id", "title", "purpose", "narration", "visual_brief",
    "on_screen_text", "entity_refs", "citation_refs",
    "duration_seconds", "transition",
]

RESEARCH_BRIEF_REQUIRED_FIELDS = [
    "artifact_type", "schema_version", "artifact_id", "created_at",
    "producer", "source_run_id", "topic", "research_question",
    "executive_summary", "key_findings", "entities", "timeline",
    "source_index", "citation_map", "open_questions", "recommended_angles",
]


def _generate_run_id() -> str:
    return f"run-{uuid.uuid4().hex[:12]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_research_brief(path: str) -> Dict[str, Any]:
    """Load and validate a ResearchBrief JSON file."""
    with open(path, "r") as f:
        brief = json.load(f)

    if brief.get("artifact_type") != "ResearchBrief":
        raise ValueError(
            f"Expected artifact_type 'ResearchBrief', got '{brief.get('artifact_type')}'"
        )

    missing = [f for f in RESEARCH_BRIEF_REQUIRED_FIELDS if f not in brief]
    if missing:
        raise ValueError(f"ResearchBrief missing required fields: {missing}")

    return brief


def list_research_brief_fixtures() -> List[str]:
    """List available canonical ResearchBrief fixture names.

    Returns:
        List of fixture names (without .json extension) found in fixtures/research_briefs/.
    """
    if not os.path.isdir(FIXTURES_DIR):
        return []
    return [
        os.path.splitext(f)[0] for f in sorted(os.listdir(FIXTURES_DIR))
        if f.endswith(".json")
    ]


def load_research_brief_fixture(name: str) -> Dict[str, Any]:
    """Load a canonical ResearchBrief fixture by name.

    Fixtures live in fixtures/research_briefs/ and represent canonical
    outputs from content-research-pipeline. This provides a stable input
    path that does not depend on free-form prompt-only behavior.

    Args:
        name: Fixture name (e.g. 'jwst_canonical'). The .json extension
              is appended automatically if not present.

    Returns:
        A validated ResearchBrief dict.

    Raises:
        FileNotFoundError: If the fixture does not exist.
        ValueError: If the fixture is not a valid ResearchBrief.
    """
    if not name.endswith(".json"):
        name = f"{name}.json"
    path = os.path.join(FIXTURES_DIR, name)
    return load_research_brief(path)


def generate_scene_plan(
    brief: Dict[str, Any],
    narrative_goal: Optional[str] = None,
    target_audience: str = "general educated audience",
    style_profile: Optional[Dict[str, str]] = None,
    source_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a contract-valid ScenePlan from a ResearchBrief.

    This is the deterministic/template-based path that does not require
    an LLM. It builds scenes directly from the structured research brief
    fields (key_findings, entities, timeline, recommended_angles).

    Args:
        brief: A validated ResearchBrief dict.
        narrative_goal: Override narrative goal (defaults to research_question).
        target_audience: Target audience description.
        style_profile: Visual/tonal style dict.
        source_run_id: Run ID linking back to the research pipeline run.

    Returns:
        A contract-valid ScenePlan dict.
    """
    topic = brief["topic"]
    run_id = source_run_id or _generate_run_id()

    if narrative_goal is None:
        narrative_goal = (
            brief.get("research_question")
            or f"Explain {topic.replace('_', ' ')}"
        )

    if style_profile is None:
        style_profile = {
            "tone": "wonder + scientific clarity",
            "visual_style": "cinematic scientific explainer",
        }

    scenes = _build_scenes_from_brief(brief)

    scene_plan: Dict[str, Any] = {
        "artifact_type": "ScenePlan",
        "schema_version": SCHEMA_VERSION,
        "artifact_id": f"scene-plan-{uuid.uuid4().hex[:8]}",
        "created_at": _now_iso(),
        "producer": PRODUCER,
        "source_run_id": run_id,
        "topic": topic,
        "narrative_goal": narrative_goal,
        "target_audience": target_audience,
        "style_profile": style_profile,
        "scenes": scenes,
    }

    return scene_plan


def _build_scenes_from_brief(brief: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build scene list from structured ResearchBrief data.

    Strategy:
      1. Opening scene from executive_summary
      2. One scene per key_finding (up to 4)
      3. Timeline scene if timeline entries exist
      4. Closing scene from recommended_angles or open_questions
    """
    scenes: List[Dict[str, Any]] = []
    topic = brief["topic"]
    entities = brief.get("entities", [])
    entity_labels = [e.get("label", e) if isinstance(e, dict) else str(e) for e in entities]

    # --- Scene 1: Opening / Executive Summary ---
    exec_summary = brief.get("executive_summary", "")
    if exec_summary:
        narration = exec_summary
    else:
        narration = f"Welcome to our exploration of {topic.replace('_', ' ')}."

    scenes.append(_make_scene(
        index=1,
        title="Introduction",
        purpose="Set context and introduce the topic",
        narration=narration,
        visual_brief=f"Wide establishing shot introducing {topic.replace('_', ' ')}. "
                      "Cinematic space imagery with text overlay.",
        on_screen_text=brief.get("research_question", topic.replace("_", " ")),
        entity_refs=entity_labels[:3],
        citation_refs=[],
        duration_seconds=15,
        transition="fade_in",
    ))

    # --- Scenes 2-5: Key Findings ---
    findings = brief.get("key_findings", [])
    for i, finding in enumerate(findings[:4], start=2):
        if isinstance(finding, dict):
            title = finding.get("title", f"Key Finding {i - 1}")
            narration_text = finding.get("summary", finding.get("text", str(finding)))
            refs = finding.get("citation_refs", [])
        else:
            title = f"Key Finding {i - 1}"
            narration_text = str(finding)
            refs = []

        scenes.append(_make_scene(
            index=i,
            title=title,
            purpose=f"Present key finding: {title}",
            narration=narration_text,
            visual_brief=f"Visual representation of {title}. "
                          "Data visualizations and relevant imagery.",
            on_screen_text=title,
            entity_refs=entity_labels[:5],
            citation_refs=refs,
            duration_seconds=20,
            transition="cross_dissolve",
        ))

    next_index = len(scenes) + 1

    # --- Timeline Scene (if available) ---
    timeline = brief.get("timeline", [])
    if timeline:
        timeline_text_parts = []
        for entry in timeline[:5]:
            if isinstance(entry, dict):
                date = entry.get("date", entry.get("year", ""))
                event = entry.get("event", entry.get("description", str(entry)))
                timeline_text_parts.append(f"{date}: {event}")
            else:
                timeline_text_parts.append(str(entry))

        scenes.append(_make_scene(
            index=next_index,
            title="Timeline",
            purpose="Present chronological development",
            narration="Let's look at the key milestones. " + " ".join(timeline_text_parts),
            visual_brief="Animated timeline graphic showing key dates and milestones.",
            on_screen_text="Key Milestones",
            entity_refs=entity_labels[:3],
            citation_refs=[],
            duration_seconds=20,
            transition="slide_left",
        ))
        next_index += 1

    # --- Closing Scene ---
    angles = brief.get("recommended_angles", [])
    open_qs = brief.get("open_questions", [])

    if angles:
        closing_narration = "Looking ahead: " + (
            angles[0].get("description", str(angles[0]))
            if isinstance(angles[0], dict)
            else str(angles[0])
        )
    elif open_qs:
        closing_narration = "Questions remain: " + (
            open_qs[0].get("question", str(open_qs[0]))
            if isinstance(open_qs[0], dict)
            else str(open_qs[0])
        )
    else:
        closing_narration = f"Thank you for exploring {topic.replace('_', ' ')} with us."

    scenes.append(_make_scene(
        index=next_index,
        title="Conclusion",
        purpose="Wrap up and point to future directions",
        narration=closing_narration,
        visual_brief="Cinematic pull-back shot. Summary text overlay with credits.",
        on_screen_text="What's Next?",
        entity_refs=[],
        citation_refs=[],
        duration_seconds=12,
        transition="fade_out",
    ))

    return scenes


def _make_scene(
    index: int,
    title: str,
    purpose: str,
    narration: str,
    visual_brief: str,
    on_screen_text: str,
    entity_refs: List[str],
    citation_refs: List[str],
    duration_seconds: int,
    transition: str,
) -> Dict[str, Any]:
    """Create a single scene dict matching the ScenePlan contract."""
    return {
        "scene_id": f"scene-{index:03d}",
        "title": title,
        "purpose": purpose,
        "narration": narration,
        "visual_brief": visual_brief,
        "on_screen_text": on_screen_text,
        "entity_refs": entity_refs,
        "citation_refs": citation_refs,
        "duration_seconds": duration_seconds,
        "transition": transition,
    }


def validate_scene_plan(plan: Dict[str, Any]) -> List[str]:
    """
    Validate a ScenePlan dict against the shared contract.

    Returns a list of error messages. Empty list means valid.
    """
    errors: List[str] = []

    for field in SCENE_PLAN_REQUIRED_FIELDS:
        if field not in plan:
            errors.append(f"Missing required field: {field}")

    if plan.get("artifact_type") != "ScenePlan":
        errors.append(
            f"artifact_type must be 'ScenePlan', got '{plan.get('artifact_type')}'"
        )

    scenes = plan.get("scenes", [])
    if not isinstance(scenes, list):
        errors.append("'scenes' must be a list")
        return errors

    for i, scene in enumerate(scenes):
        for field in SCENE_REQUIRED_FIELDS:
            if field not in scene:
                errors.append(f"Scene {i}: missing required field '{field}'")

    return errors
