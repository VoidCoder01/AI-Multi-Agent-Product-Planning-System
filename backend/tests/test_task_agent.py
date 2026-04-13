"""Tests for global task ID renumbering (no API calls)."""

import pytest

from agents.task_agent import renumber_task_ids_globally


def test_renumber_makes_all_task_ids_unique():
    payload = {
        "tasks": [
            {
                "story_id": "STORY-1",
                "tasks": [
                    {"id": "TASK-1", "title": "a"},
                    {"id": "TASK-2", "title": "b"},
                ],
            },
            {
                "story_id": "STORY-2",
                "tasks": [
                    {"id": "TASK-1", "title": "c"},
                    {"id": "TASK-1", "title": "d"},
                ],
            },
        ]
    }
    renumber_task_ids_globally(payload)

    ids = []
    for sg in payload["tasks"]:
        for t in sg["tasks"]:
            ids.append(t["id"])

    assert len(ids) == len(set(ids)), f"duplicates: {ids}"
    assert ids == ["TASK-1", "TASK-2", "TASK-3", "TASK-4"]


def test_renumber_starts_at_one_and_sequential():
    payload = {
        "tasks": [
            {
                "story_id": "S1",
                "tasks": [{"id": "TASK-99", "title": "x"}],
            },
            {
                "story_id": "S2",
                "tasks": [{"id": "TASK-99", "title": "y"}],
            },
        ]
    }
    renumber_task_ids_globally(payload)
    ids = [t["id"] for sg in payload["tasks"] for t in sg["tasks"]]
    assert ids == ["TASK-1", "TASK-2"]


def test_empty_tasks_list():
    assert renumber_task_ids_globally({"tasks": []}) == {"tasks": []}
