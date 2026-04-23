"""Integration test: graph runs end-to-end with mocked agents."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch


def _mock_openai_response(text: str) -> MagicMock:
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = text
    mock_response.choices = [mock_choice]
    return mock_response


MOCK_BRIEF = {
    "project_name": "TestApp",
    "problem_statement": "Test problem",
    "target_users": "Testers",
    "key_features": ["Feature A", "Feature B", "Feature C"],
    "constraints": "4-week timeline",
}

MOCK_REVIEW = {
    "strengths": ["Clear scope"],
    "gaps": ["No monetization"],
    "risks_if_unaddressed": ["Revenue risk"],
    "recommended_changes": ["Add pricing"],
    "brief_critique_summary": "Solid start.",
}

MOCK_PRD = {
    "overview": "Test product overview",
    "goals": ["Goal 1", "Goal 2"],
    "user_personas": [{"name": "Tester", "description": "Tests things"}],
    "functional_requirements": ["FR1", "FR2", "FR3", "FR4", "FR5", "FR6"],
    "non_functional_requirements": ["NFR1", "NFR2", "NFR3", "NFR4", "NFR5"],
    "success_metrics": ["M1", "M2", "M3", "M4", "M5"],
    "mvp_scope": {
        "must_have_features": ["Core feature"],
        "explicitly_deferred": ["Advanced stuff"],
        "mvp_build_assumption": "2 devs, 3 months",
    },
    "phased_roadmap": {
        "phase_2_growth": ["Growth features"],
        "phase_3_advanced": ["Advanced features"],
    },
    "risks_and_tradeoffs": {
        "key_product_risks": ["Risk 1"],
        "product_tradeoffs": [
            {"decision": "D1", "chosen": "C1", "sacrificed": "S1"},
            {"decision": "D2", "chosen": "C2", "sacrificed": "S2"},
            {"decision": "D3", "chosen": "C3", "sacrificed": "S3"},
        ],
        "technical_risks": ["TR1"],
        "gtm_risks": ["GTM1"],
    },
    "decision_log": [
        {"area": "A1", "decision": "D1", "rationale": "R1", "defer_to": "never"},
        {"area": "A2", "decision": "D2", "rationale": "R2", "defer_to": "phase 2"},
    ],
}

MOCK_ARCH = {
    "system_overview": "Simple architecture",
    "services": [
        {"name": "API", "responsibility": "Core", "key_interfaces": "REST", "notes": ""}
    ],
    "suggested_stack": {
        "frontend": "React",
        "backend": "FastAPI",
        "data": "PostgreSQL",
        "infra": "AWS",
    },
    "data_flow_textual": "Client -> API -> DB",
    "scalability_considerations": ["Horizontal scaling"],
    "security_and_compliance": ["TLS"],
    "tradeoffs_made": ["Monolith first"],
}

MOCK_EPICS = {
    "epics": [
        {
            "id": "EPIC-1",
            "title": "User management",
            "description": "Core user features",
            "success_criteria": "80% onboarding completion",
            "stories": [
                {
                    "id": "STORY-1",
                    "title": "As a user, I want to register, so that I can access the app",
                    "priority": "High",
                    "release_phase": "MVP",
                    "acceptance_criteria": ["Registration works with valid email"],
                }
            ],
        }
    ]
}

MOCK_SCRUM_REVIEW = {
    "prd_alignment": "high",
    "what_works": ["Clear scope"],
    "concerns": [],
    "backlog_risks": [],
    "recommended_changes": [],
    "validation_summary": "Ready to decompose.",
}

MOCK_FEASIBILITY = {
    "overall_feasible": True,
    "prd_alignment_notes": ["Aligned"],
    "overscoped_or_risky_items": [],
    "technical_feasibility_concerns": [],
    "implementability_score": "high",
    "recommendations": ["Proceed as planned"],
}

MOCK_TASKS = {
    "tasks": [
        {
            "story_id": "STORY-1",
            "tasks": [
                {
                    "id": "TASK-1",
                    "title": "Create user model",
                    "description": "Define user schema in DB",
                    "subtasks": ["Add migration", "Create model class", "Add indexes"],
                }
            ],
        }
    ]
}

MOCK_EVAL = {
    "brief_eval": {"relevance_score": 8, "hallucination_score": 1, "feedback": "Good"},
}


@patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
@patch("agents.base.OpenAI")
def test_full_graph_pipeline(mock_cls):
    """End-to-end graph execution with mocked LLM responses."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    responses = [
        json.dumps(MOCK_BRIEF),
        json.dumps(MOCK_REVIEW),
        json.dumps(MOCK_PRD),
        json.dumps(MOCK_ARCH),
        json.dumps(MOCK_SCRUM_REVIEW),
        json.dumps(MOCK_EPICS),
        json.dumps(MOCK_FEASIBILITY),
        json.dumps(MOCK_TASKS),
        # Evaluator makes up to 2 calls (brief + prd)
        json.dumps(MOCK_EVAL),
        json.dumps(MOCK_EVAL),
    ]
    mock_client.chat.completions.create.side_effect = [
        _mock_openai_response(r) for r in responses
    ]

    from backend.orchestrator import Orchestrator

    orch = Orchestrator()
    result = orch.run_workflow(
        "A marketplace for freelancers",
        {
            "q1": "Freelancers and businesses",
            "q2": "MVP is search and profiles",
            "q3": "No special compliance",
            "q4": "Commission model",
        },
        questions=["Q1?", "Q2?", "Q3?", "Q4?"],
    )

    assert result.get("error") is None, f"Pipeline error: {result.get('error')}"
    assert result.get("halt_reason") is None
    assert "project_brief" in result
    assert "prd" in result
    assert "epics_stories" in result
    assert "tasks" in result
    assert result["project_brief"].get("project_name") is not None
