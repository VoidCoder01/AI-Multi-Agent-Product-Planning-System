"""Tests for prompt_loader (no LLM calls)."""

import pytest

from backend.prompt_loader import (
    PromptTemplateError,
    build_prompt,
    load_prompt,
    render_template,
)


def test_load_prd_v1_has_metadata():
    p = load_prompt("prd/v1.md")
    assert p.name == "pm_prd"
    assert p.version == "v1"
    assert p.max_tokens == 8192


def test_build_injects_shared_constraints():
    p = load_prompt("prd/v1.md")
    out = build_prompt(p, {})
    assert "Return ONLY structured output" in out  # from shared/constraints.md
    assert "OUTPUT FORMAT" in out
    assert "{{" not in out


def test_render_template_missing_var_raises():
    with pytest.raises(PromptTemplateError):
        render_template("Hello {{x}}", {})


def test_user_template_no_output_format_section():
    p = load_prompt("pm/prd_user_v1.md")
    out = build_prompt(
        p,
        {"project_brief_json": "{}", "brief_review_section": ""},
        validate_output_format=False,
    )
    assert "{{" not in out
