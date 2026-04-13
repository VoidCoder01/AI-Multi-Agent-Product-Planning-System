#!/usr/bin/env python3
"""Validate generated documentation for duplicate IDs and basic structure."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def validate_task_ids(data: dict) -> tuple[bool, list[str]]:
    """Check for duplicate task IDs."""
    errors: list[str] = []
    tasks_section = data.get("tasks", {})
    if not isinstance(tasks_section, dict):
        errors.append("'tasks' must be an object with a 'tasks' array")
        return False, errors

    if tasks_section.get("error") and not tasks_section.get("tasks"):
        errors.append(
            f"Task generation failed (legacy/error shape): {tasks_section.get('error')!r}. "
            "Regenerate with the current TaskAgent."
        )
        return False, errors

    story_tasks = tasks_section.get("tasks", [])
    if not isinstance(story_tasks, list):
        errors.append("'tasks.tasks' must be a list")
        return False, errors

    all_task_ids: list[str] = []
    for story_group in story_tasks:
        if not isinstance(story_group, dict):
            continue
        for task in story_group.get("tasks") or []:
            if isinstance(task, dict):
                tid = task.get("id", "")
                all_task_ids.append(tid)

    if not all_task_ids:
        errors.append("No tasks found in output")
        return False, errors

    counts = Counter(all_task_ids)
    duplicates = [tid for tid, c in counts.items() if c > 1 and tid]
    if duplicates:
        errors.append(
            f"Found {len(all_task_ids) - len(set(all_task_ids))} duplicate task ID(s)"
        )
        errors.append(f"Duplicate IDs (sample): {duplicates[:10]}")
        return False, errors

    for tid in all_task_ids:
        if not tid or not str(tid).startswith("TASK-"):
            errors.append(f"Invalid task ID format: {tid!r}")
            return False, errors
        try:
            int(str(tid).split("-", 1)[1])
        except (IndexError, ValueError):
            errors.append(f"Task ID suffix is not numeric: {tid!r}")
            return False, errors

    print(f"✅ Task IDs validated: {len(all_task_ids)} unique tasks")
    return True, []


def validate_story_ids(data: dict) -> tuple[bool, list[str]]:
    """Check for duplicate story IDs."""
    errors: list[str] = []
    epics = data.get("epics_stories", {}).get("epics", [])
    if not isinstance(epics, list):
        errors.append("Missing epics_stories.epics")
        return False, errors

    all_story_ids: list[str] = []
    for epic in epics:
        if not isinstance(epic, dict):
            continue
        for story in epic.get("stories") or []:
            if isinstance(story, dict):
                all_story_ids.append(story.get("id", ""))

    duplicates = [sid for sid, c in Counter(all_story_ids).items() if c > 1 and sid]
    if duplicates:
        errors.append(f"Found duplicate story IDs: {duplicates}")
        return False, errors

    print(f"✅ Story IDs validated: {len(all_story_ids)} stories ({len(set(all_story_ids))} unique IDs)")
    return True, []


def validate_epic_ids(data: dict) -> tuple[bool, list[str]]:
    """Check for duplicate epic IDs."""
    errors: list[str] = []
    epics = data.get("epics_stories", {}).get("epics", [])
    if not isinstance(epics, list):
        errors.append("Missing epics_stories.epics")
        return False, errors

    epic_ids = [e.get("id", "") for e in epics if isinstance(e, dict)]
    duplicates = [eid for eid, c in Counter(epic_ids).items() if c > 1 and eid]
    if duplicates:
        errors.append(f"Found duplicate epic IDs: {duplicates}")
        return False, errors

    print(f"✅ Epic IDs validated: {len(epic_ids)} unique epics")
    return True, []


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python backend/validate_output.py <path_to.json>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    if not json_path.is_file():
        print(f"❌ File not found: {json_path}")
        sys.exit(1)

    print(f"Validating: {json_path}")
    print("=" * 60)

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    all_passed = True
    for name, validator in (
        ("Epic IDs", validate_epic_ids),
        ("Story IDs", validate_story_ids),
        ("Task IDs", validate_task_ids),
    ):
        passed, errs = validator(data)
        if not passed:
            all_passed = False
            print(f"\n❌ {name} validation failed:")
            for e in errs:
                print(f"   {e}")

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All validations passed!")
        sys.exit(0)
    print("❌ Validation failed — see errors above")
    sys.exit(1)


if __name__ == "__main__":
    main()
