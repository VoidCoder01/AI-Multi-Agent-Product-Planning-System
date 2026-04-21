"""Evaluation framework to measure quality (Hallucination, Relevance)."""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from agents.json_utils import parse_llm_json

class EvaluatorAgent(BaseAgent):
    """Measures LLM output quality post-generation."""
    
    audit_name = "EVALUATOR_AGENT"

    def evaluate_output(self, original_query: str, generated_document: str) -> dict[str, Any]:
        """Returns a score and rationale for the output quality."""
        system_prompt = (
            "You are an expert QA reviewer. Evaluate the provided document against the original user query. "
            "Output precisely valid JSON with these keys: "
            "'relevance_score' (1-10), "
            "'hallucination_score' (1-10; higher means MORE hallucinated/incorrect), "
            "'feedback' (short string)."
        )
        user_message = f"Query: {original_query}\n\nDocument: {generated_document[:3000]}"
        
        raw_text = self.call_llm(
            system_prompt,
            user_message,
            max_tokens=300,
            phase="quality_evaluation"
        )
        try:
            data = parse_llm_json(raw_text)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
            
        return {
            "relevance_score": 0,
            "hallucination_score": 10,
            "feedback": "Failed to parse evaluation metric."
        }
