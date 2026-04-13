"""Tests for validation helpers in schemas.validation."""

from __future__ import annotations

from schemas.validation import (
    validate_architecture,
    validate_epics_stories,
    validate_prd,
    validate_project_brief,
    validate_qa_context,
)


class TestValidateQA:
    def test_valid_qa(self):
        ok, _ = validate_qa_context([("Q1?", "Answer one"), ("Q2?", "Answer two")])
        assert ok is True

    def test_too_few_pairs(self):
        ok, errs = validate_qa_context([("Q1?", "A1")], min_pairs=2)
        assert ok is False
        assert any("at least" in e for e in errs)

    def test_empty_answers_fail(self):
        ok, _ = validate_qa_context(
            [("Q1?", ""), ("Q2?", ""), ("Q3?", "")],
            min_pairs=2,
            min_answer_len=1,
            min_fill_ratio=0.5,
        )
        assert ok is False


class TestValidateBrief:
    def test_valid_brief(self):
        ok, _ = validate_project_brief(
            {
                "project_name": "Test",
                "problem_statement": "A real problem",
                "target_users": "Developers",
                "key_features": ["Feature 1"],
                "constraints": "None",
            }
        )
        assert ok is True

    def test_missing_fields(self):
        ok, errs = validate_project_brief({})
        assert ok is False
        assert len(errs) == 5


class TestValidateArchitecture:
    def test_valid_architecture(self):
        ok, _ = validate_architecture(
            {
                "services": [{"name": "API"}],
                "suggested_stack": {"frontend": "React"},
                "data_flow_textual": "Client -> Server -> DB",
            }
        )
        assert ok is True

    def test_error_shape_fails(self):
        ok, _ = validate_architecture({"error": "parse_failed"})
        assert ok is False


class TestValidatePRDAndEpics:
    def test_valid_prd_and_epics(self):
        prd_ok, _ = validate_prd(
            {
                "overview": "Overview",
                "goals": ["Goal 1"],
                "functional_requirements": ["FR1"],
                "non_functional_requirements": ["NFR1"],
                "success_metrics": ["M1"],
                "mvp_scope": {
                    "must_have_features": ["A"],
                    "explicitly_deferred": ["B"],
                    "mvp_build_assumption": "2 engineers",
                },
                "phased_roadmap": {
                    "phase_2_growth": ["C"],
                    "phase_3_advanced": ["D"],
                },
                "risks_and_tradeoffs": {
                    "key_product_risks": ["R1"],
                    "product_tradeoffs": [
                        {"decision": "D1", "chosen": "C1", "sacrificed": "S1"},
                        {"decision": "D2", "chosen": "C2", "sacrificed": "S2"},
                    ],
                    "technical_risks": ["R2"],
                    "gtm_risks": ["R3"],
                },
                "decision_log": [
                    {"area": "A1", "decision": "D1", "rationale": "R1", "defer_to": "never"},
                    {"area": "A2", "decision": "D2", "rationale": "R2", "defer_to": "phase 2"},
                ],
            }
        )
        assert prd_ok is True

        epics_ok, _ = validate_epics_stories(
            {
                "epics": [
                    {
                        "id": "EPIC-1",
                        "success_criteria": "80% completion",
                        "stories": [
                            {
                                "id": "STORY-1",
                                "priority": "High",
                                "release_phase": "MVP",
                            }
                        ],
                    }
                ]
            }
        )
        assert epics_ok is True
