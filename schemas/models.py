"""API-oriented types (Pydantic) — optional; graph state uses schemas.state.PlanningState."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProductIdeaBody(BaseModel):
    product_idea: str = Field(..., min_length=1)


class GenerateBody(BaseModel):
    product_idea: str = Field(..., min_length=1)
    answers: dict = Field(default_factory=dict)
    questions: list[str] | None = None
