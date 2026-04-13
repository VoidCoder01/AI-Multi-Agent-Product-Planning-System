"""Unit tests for all agents; LLM calls are mocked."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest


def _mock_anthropic_response(text: str) -> MagicMock:
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.text = text
    mock_response.content = [mock_block]
    return mock_response


@pytest.fixture
def mock_anthropic():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("agents.base.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            yield mock_client


class TestClarificationAgent:
    def test_ask_questions_returns_list(self, mock_anthropic):
        mock_anthropic.messages.create.return_value = _mock_anthropic_response(
            json.dumps(
                [
                    "What users?",
                    "What MVP?",
                    "What constraints?",
                    "What monetization?",
                    "What differentiator?",
                ]
            )
        )
        from agents.clarification_agent import ClarificationAgent

        agent = ClarificationAgent()
        qs = agent.ask_questions("A marketplace for freelancers")
        assert isinstance(qs, list)
        assert len(qs) >= 3
        assert all("?" in q for q in qs)

    def test_ask_questions_fallback_on_bad_json(self, mock_anthropic):
        mock_anthropic.messages.create.return_value = _mock_anthropic_response(
            "This is not JSON at all"
        )
        from agents.clarification_agent import ClarificationAgent

        agent = ClarificationAgent()
        qs = agent.ask_questions("A marketplace")
        assert isinstance(qs, list)
        assert len(qs) >= 3


class TestRequirementAgent:
    def test_create_project_brief(self, mock_anthropic):
        brief = {
            "project_name": "FreelanceHub",
            "problem_statement": "Freelancers lack a unified marketplace.",
            "target_users": "Independent contractors and small businesses",
            "key_features": ["Profile creation", "Job matching", "Payments"],
            "constraints": "3-month MVP timeline",
        }
        mock_anthropic.messages.create.return_value = _mock_anthropic_response(
            json.dumps(brief)
        )
        from agents.requirement_agent import RequirementAgent

        agent = RequirementAgent()
        result = agent.create_project_brief("marketplace", [("Who?", "freelancers")])
        assert result.get("project_name") == "FreelanceHub"
        assert "error" not in result


class TestPMAgent:
    def test_review_and_prd(self, mock_anthropic):
        review = {
            "strengths": ["Clear scope"],
            "gaps": ["Missing monetization"],
            "risks_if_unaddressed": ["Revenue uncertainty"],
            "recommended_changes": ["Add pricing model"],
            "brief_critique_summary": "Needs monetization clarity.",
        }
        prd = {
            "overview": "A freelancer marketplace...",
            "goals": ["100 signups in month 1"],
            "user_personas": [{"name": "Freelancer", "description": "..."}],
            "functional_requirements": ["FR1", "FR2", "FR3", "FR4", "FR5", "FR6"],
            "non_functional_requirements": ["NFR1", "NFR2", "NFR3", "NFR4", "NFR5"],
            "success_metrics": ["SM1", "SM2", "SM3", "SM4", "SM5"],
            "mvp_scope": {
                "must_have_features": ["Profiles", "Search"],
                "explicitly_deferred": ["Advanced analytics"],
                "mvp_build_assumption": "2 engineers, 3 months",
            },
            "phased_roadmap": {
                "phase_2_growth": ["Analytics dashboard"],
                "phase_3_advanced": ["AI matching"],
            },
            "risks_and_tradeoffs": {
                "key_product_risks": ["Low adoption"],
                "product_tradeoffs": [
                    {
                        "decision": "MVP first",
                        "chosen": "Speed",
                        "sacrificed": "Features",
                    },
                    {
                        "decision": "No mobile",
                        "chosen": "Web focus",
                        "sacrificed": "Mobile UX",
                    },
                ],
                "technical_risks": ["Scale concerns"],
                "gtm_risks": ["Marketing budget"],
            },
            "decision_log": [
                {
                    "area": "Platform",
                    "decision": "Web only",
                    "rationale": "Speed",
                    "defer_to": "phase 2",
                },
                {
                    "area": "Payments",
                    "decision": "Stripe",
                    "rationale": "Standard",
                    "defer_to": "never",
                },
            ],
        }
        mock_anthropic.messages.create.side_effect = [
            _mock_anthropic_response(json.dumps(review)),
            _mock_anthropic_response(json.dumps(prd)),
        ]
        from agents.pm_agent import PMAgent

        agent = PMAgent()
        r = agent.review_project_brief({"project_name": "Test"})
        assert "strengths" in r
        p = agent.create_prd({"project_name": "Test"}, brief_review=r)
        assert "overview" in p


class TestScrumAgent:
    def test_epics_and_stories(self, mock_anthropic):
        epics = {
            "epics": [
                {
                    "id": "EPIC-1",
                    "title": "User onboarding",
                    "description": "...",
                    "success_criteria": "80% completion rate",
                    "stories": [
                        {
                            "id": "STORY-1",
                            "title": "As a user, I want to register, so that I can access the platform",
                            "priority": "High",
                            "release_phase": "MVP",
                            "acceptance_criteria": [
                                "Given valid email, registration succeeds"
                            ],
                        }
                    ],
                }
            ]
        }
        review = {
            "prd_alignment": "high",
            "what_works": ["Good"],
            "concerns": [],
            "backlog_risks": [],
            "recommended_changes": [],
            "validation_summary": "OK",
        }
        mock_anthropic.messages.create.side_effect = [
            _mock_anthropic_response(json.dumps(review)),
            _mock_anthropic_response(json.dumps(epics)),
        ]
        from agents.scrum_agent import ScrumAgent

        agent = ScrumAgent()
        r = agent.review_prd({"overview": "test"})
        assert r.get("prd_alignment") == "high"
        es = agent.create_epics_and_stories({"overview": "test"}, prd_review=r)
        assert "epics" in es


class TestArchitectAgent:
    def test_create_architecture(self, mock_anthropic):
        arch = {
            "system_overview": "Microservices architecture...",
            "services": [
                {
                    "name": "API Gateway",
                    "responsibility": "Routing",
                    "key_interfaces": "REST",
                    "notes": "",
                }
            ],
            "suggested_stack": {
                "frontend": "React",
                "backend": "FastAPI",
                "data": "PostgreSQL",
                "infra": "AWS",
            },
            "data_flow_textual": "Client -> API -> DB",
            "scalability_considerations": ["Horizontal scaling"],
            "security_and_compliance": ["TLS everywhere"],
            "tradeoffs_made": ["Monolith-first approach"],
        }
        mock_anthropic.messages.create.return_value = _mock_anthropic_response(
            json.dumps(arch)
        )
        from agents.architect_agent import ArchitectAgent

        agent = ArchitectAgent()
        result = agent.create_architecture({"overview": "test"})
        assert "services" in result
        assert "error" not in result
