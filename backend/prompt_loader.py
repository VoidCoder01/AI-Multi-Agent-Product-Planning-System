"""Load versioned prompts from Markdown + YAML frontmatter; strict {{var}} templating."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# This file lives in backend/; repo root is one level up.
_REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_ROOT = _REPO_ROOT / "backend" / "prompts"

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


class PromptLoadError(ValueError):
    """Failed to load or parse a prompt file."""


class PromptTemplateError(ValueError):
    """Template rendering or validation failed."""


@dataclass(frozen=True)
class LoadedPrompt:
    """Prompt metadata + raw template body (may contain {{placeholders}})."""

    name: str
    version: str
    temperature: float
    max_tokens: int
    relative_path: str
    body: str


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    if not raw.lstrip().startswith("---"):
        raise PromptLoadError("Missing YAML frontmatter (expected --- at start)")
    parts = raw.split("---", 2)
    if len(parts) < 3:
        raise PromptLoadError("Invalid frontmatter block")
    fm_raw, body = parts[1], parts[2]
    try:
        meta = yaml.safe_load(fm_raw) or {}
    except yaml.YAMLError as e:
        raise PromptLoadError(f"Invalid YAML frontmatter: {e}") from e
    if not isinstance(meta, dict):
        raise PromptLoadError("Frontmatter must be a mapping")
    return meta, body.lstrip("\n")


def _require_meta(meta: dict[str, Any], key: str) -> Any:
    if key not in meta:
        raise PromptLoadError(f"Frontmatter missing required key: {key}")
    return meta[key]


def load_prompt(relative_path: str) -> LoadedPrompt:
    """
    Load a prompt from backend/prompts/<relative_path>.
    relative_path examples: "prd/v1.md", "shared/constraints.md"
    """
    rel = relative_path.strip().replace("\\", "/")
    path = (PROMPTS_ROOT / rel).resolve()
    if not str(path).startswith(str(PROMPTS_ROOT.resolve())):
        raise PromptLoadError(f"Path escapes prompts root: {relative_path}")
    if not path.is_file():
        raise PromptLoadError(f"Prompt file not found: {path}")
    raw = path.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(raw)
    name = str(_require_meta(meta, "name"))
    version = str(_require_meta(meta, "version"))
    temperature = float(_require_meta(meta, "temperature"))
    max_tokens = int(_require_meta(meta, "max_tokens"))
    return LoadedPrompt(
        name=name,
        version=version,
        temperature=temperature,
        max_tokens=max_tokens,
        relative_path=rel,
        body=body,
    )


def load_shared_constraints() -> str:
    """Body text from backend/prompts/shared/constraints.md (for {{shared_constraints}})."""
    lp = load_prompt("shared/constraints.md")
    return lp.body.strip()


def _stringify(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


def render_template(template: str, variables: dict[str, Any]) -> str:
    """Replace {{name}} placeholders; every placeholder must be present in variables."""

    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in variables:
            raise PromptTemplateError(f"Missing template variable: {key}")
        return _stringify(variables[key])

    out = _PLACEHOLDER_RE.sub(repl, template)
    if _PLACEHOLDER_RE.search(out):
        raise PromptTemplateError("Unresolved {{placeholders}} remain after render")
    return out


def _inject_shared_if_needed(body: str, variables: dict[str, Any]) -> dict[str, Any]:
    if "{{shared_constraints}}" in body and "shared_constraints" not in variables:
        merged = dict(variables)
        merged["shared_constraints"] = load_shared_constraints()
        return merged
    return variables


def ensure_output_format_section(rendered: str) -> None:
    """Fail closed if OUTPUT FORMAT is absent (case-insensitive)."""
    if "OUTPUT FORMAT" not in rendered.upper():
        raise PromptTemplateError(
            "Rendered prompt must contain an 'OUTPUT FORMAT' section for strict validation"
        )


def ensure_no_unresolved_placeholders(rendered: str) -> None:
    if _PLACEHOLDER_RE.search(rendered):
        raise PromptTemplateError(
            f"Unresolved placeholders remain: {rendered[:400]!r}..."
        )


def build_prompt(
    loaded: LoadedPrompt,
    variables: dict[str, Any] | None = None,
    *,
    validate_output_format: bool = True,
) -> str:
    """
    Render a loaded prompt template. All {{vars}} must resolve (shared_constraints auto-injected).
    Optionally require an OUTPUT FORMAT section in the rendered text.
    """
    vars_ = _inject_shared_if_needed(loaded.body, dict(variables or {}))
    rendered = render_template(loaded.body, vars_)
    ensure_no_unresolved_placeholders(rendered)
    if validate_output_format:
        ensure_output_format_section(rendered)
    return rendered


@dataclass(frozen=True)
class PromptAuditRecord:
    """Structured audit payload for logging."""

    prompt_name: str
    prompt_version: str
    prompt_path: str
    temperature: float
    max_tokens: int
    variable_keys: tuple[str, ...]
    rendered_preview: str


def make_prompt_audit(
    loaded: LoadedPrompt,
    variables: dict[str, Any] | None,
    rendered: str,
    *,
    preview_max: int = 8000,
) -> PromptAuditRecord:
    keys = sorted((variables or {}).keys())
    prev = rendered if len(rendered) <= preview_max else rendered[: preview_max - 3] + "..."
    return PromptAuditRecord(
        prompt_name=loaded.name,
        prompt_version=loaded.version,
        prompt_path=loaded.relative_path,
        temperature=loaded.temperature,
        max_tokens=loaded.max_tokens,
        variable_keys=tuple(keys),
        rendered_preview=prev,
    )


def log_prompt_run(audit: PromptAuditRecord) -> None:
    """Log prompt version, variable keys, and rendered preview."""
    logger.info(
        "prompt_audit name=%s version=%s path=%s vars=%s",
        audit.prompt_name,
        audit.prompt_version,
        audit.prompt_path,
        list(audit.variable_keys),
    )
    logger.debug("prompt_rendered_preview:\n%s", audit.rendered_preview)


def prepare_rendered(
    relative_path: str,
    variables: dict[str, Any] | None = None,
    *,
    validate_output_format: bool = True,
) -> tuple[str, LoadedPrompt, dict[str, Any]]:
    """
    Load + render + validate + audit log. Returns rendered text, LoadedPrompt, and metadata for call_llm.
    """
    loaded = load_prompt(relative_path)
    rendered = build_prompt(
        loaded,
        variables,
        validate_output_format=validate_output_format,
    )
    audit = make_prompt_audit(loaded, variables, rendered)
    log_prompt_run(audit)
    meta = {
        "prompt_name": audit.prompt_name,
        "prompt_version": audit.prompt_version,
        "prompt_path": audit.prompt_path,
        "variable_keys": list(audit.variable_keys),
        "rendered_prompt": audit.rendered_preview,
    }
    return rendered, loaded, meta
