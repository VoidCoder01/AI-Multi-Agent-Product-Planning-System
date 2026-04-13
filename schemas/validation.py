"""Lightweight validation between agents (structure + non-empty checks)."""

from __future__ import annotations

from typing import Any


def validate_qa_context(
    qa_pairs: list[tuple[str, str]],
    *,
    min_pairs: int = 2,
    min_answer_len: int = 4,
    min_fill_ratio: float = 0.35,
) -> tuple[bool, list[str]]:
    """Return (ok, error_messages)."""
    errs: list[str] = []
    if len(qa_pairs) < min_pairs:
        errs.append(f"Need at least {min_pairs} question–answer pairs; got {len(qa_pairs)}.")
        return False, errs
    nonempty = sum(1 for _, a in qa_pairs if len((a or "").strip()) >= min_answer_len)
    ratio = nonempty / max(len(qa_pairs), 1)
    if ratio < min_fill_ratio:
        errs.append(
            f"Too many empty or very short answers (need ≥{min_fill_ratio:.0%} with "
            f"≥{min_answer_len} chars; got {ratio:.0%})."
        )
        return False, errs
    return True, []


def validate_project_brief(brief: dict[str, Any]) -> tuple[bool, list[str]]:
    errs: list[str] = []
    required = ("project_name", "problem_statement", "target_users", "key_features", "constraints")
    for k in required:
        v = brief.get(k)
        if v is None or (isinstance(v, str) and not str(v).strip()) or (isinstance(v, list) and len(v) == 0):
            errs.append(f"Missing or empty: {k}")
    return (len(errs) == 0, errs)


def validate_prd(prd: dict[str, Any]) -> tuple[bool, list[str]]:
    errs: list[str] = []
    legacy = ("overview", "goals", "functional_requirements", "non_functional_requirements", "success_metrics")
    for k in legacy:
        v = prd.get(k)
        if v is None:
            errs.append(f"Missing PRD key: {k}")
        elif isinstance(v, list) and len(v) == 0:
            errs.append(f"Empty list: {k}")
        elif isinstance(v, str) and not v.strip():
            errs.append(f"Empty string: {k}")

    mvp = prd.get("mvp_scope")
    if not isinstance(mvp, dict):
        errs.append("Missing or invalid mvp_scope object")
    else:
        if not (mvp.get("must_have_features") or []):
            errs.append("mvp_scope.must_have_features must be non-empty")
        if not (mvp.get("explicitly_deferred") or []):
            errs.append("mvp_scope.explicitly_deferred should list deferred items")

    phases = prd.get("phased_roadmap")
    if not isinstance(phases, dict):
        errs.append("Missing or invalid phased_roadmap")
    else:
        if not (phases.get("phase_2_growth") or []):
            errs.append("phased_roadmap.phase_2_growth should be non-empty")
        if not (phases.get("phase_3_advanced") or []):
            errs.append("phased_roadmap.phase_3_advanced should be non-empty")

    risks = prd.get("risks_and_tradeoffs")
    if not isinstance(risks, dict):
        errs.append("Missing or invalid risks_and_tradeoffs")
    else:
        for rk in ("key_product_risks", "technical_risks", "gtm_risks"):
            if not (risks.get(rk) or []):
                errs.append(f"risks_and_tradeoffs.{rk} should be non-empty")
        pt = risks.get("product_tradeoffs") or []
        if not isinstance(pt, list) or len(pt) < 2:
            errs.append("risks_and_tradeoffs.product_tradeoffs must have at least 2 items")

    dl = prd.get("decision_log") or []
    if not isinstance(dl, list) or len(dl) < 2:
        errs.append("decision_log must have at least 2 entries")

    return (len(errs) == 0, errs)


def validate_architecture(arch: dict[str, Any]) -> tuple[bool, list[str]]:
    errs: list[str] = []
    if arch.get("error"):
        errs.append("architecture agent returned error shape")
        return False, errs
    if not (arch.get("services") or []):
        errs.append("architecture.services must be non-empty")
    if not isinstance(arch.get("suggested_stack"), dict):
        errs.append("architecture.suggested_stack must be an object")
    if not (arch.get("data_flow_textual") or "").strip():
        errs.append("architecture.data_flow_textual must be non-empty")
    return (len(errs) == 0, errs)


def validate_epics_stories(es: dict[str, Any]) -> tuple[bool, list[str]]:
    """Structural check; warnings can be non-blocking at graph level."""
    errs: list[str] = []
    epics = es.get("epics") if isinstance(es, dict) else None
    if not isinstance(epics, list) or len(epics) == 0:
        errs.append("epics_stories.epics must be a non-empty list")
        return False, errs
    for epic in epics:
        if not isinstance(epic, dict):
            continue
        sc = epic.get("success_criteria")
        if not sc or (isinstance(sc, str) and len(sc.strip()) < 8):
            errs.append(f"Epic {epic.get('id')} missing measurable success_criteria")
        for story in epic.get("stories") or []:
            if not isinstance(story, dict):
                continue
            pr = str(story.get("priority") or "").strip().title()
            if pr not in ("High", "Medium", "Low"):
                errs.append(f"Story {story.get('id')} missing valid priority (High|Medium|Low)")
            rp = str(story.get("release_phase") or "").strip()
            if rp.replace("-", " ").lower() not in ("mvp", "post mvp", "post-mvp"):
                errs.append(f"Story {story.get('id')} missing MVP|Post-MVP tag")
    return (len(errs) == 0, errs)


def run_final_pipeline_validation(state: dict[str, Any]) -> dict[str, Any]:
    """
    Pre-output coherence check — does not replace per-stage validators.
    Returns { "passed", "issues", "warnings" }.
    """
    issues: list[str] = []
    warnings: list[str] = []

    es = state.get("epics_stories") or {}
    epic_ok, epic_errs = validate_epics_stories(es)
    if not epic_ok:
        for e in epic_errs:
            warnings.append(f"Epic/story structure: {e}")

    prd = state.get("prd") or {}
    tasks = state.get("tasks") or {}
    feas = state.get("task_feasibility") or {}

    if isinstance(feas, dict) and feas.get("implementability_score") == "low":
        warnings.append("Task feasibility review scored implementability as low — review recommendations.")

    if isinstance(feas, dict):
        overs = feas.get("overscoped_or_risky_items") or []
        if isinstance(overs, list) and len(overs) > 4:
            warnings.append("Many items flagged as overscoped — consider trimming MVP.")

    # PRD ↔ tasks traceability (light): ensure task story_ids exist in epics
    story_ids: set[str] = set()
    for epic in (es.get("epics") or []):
        if not isinstance(epic, dict):
            continue
        for s in epic.get("stories") or []:
            if isinstance(s, dict) and s.get("id"):
                story_ids.add(s["id"])

    task_groups = tasks.get("tasks") if isinstance(tasks, dict) else None
    if isinstance(task_groups, list):
        for grp in task_groups:
            if not isinstance(grp, dict):
                continue
            sid = grp.get("story_id")
            if sid and story_ids and sid not in story_ids:
                issues.append(f"Tasks reference unknown story_id: {sid}")

    goals = prd.get("goals") or []
    if isinstance(goals, list) and len(goals) > 12:
        warnings.append("PRD lists many goals — possible over-scoping.")

    passed = len(issues) == 0
    return {
        "passed": passed,
        "issues": issues,
        "warnings": warnings,
    }
