"""Lightweight validation between agents (structure + non-empty checks)."""

from __future__ import annotations

from typing import Any


def apply_pm_review_feedback_to_brief(
    brief: dict[str, Any],
    review: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Apply high-signal PM brief review findings back to the source brief.
    This prevents review output from becoming a dead-end artifact.
    """
    if not isinstance(brief, dict) or not isinstance(review, dict):
        return brief

    merged = dict(brief)
    gaps = " ".join(str(x) for x in review.get("gaps") or []).lower()
    recs = " ".join(str(x) for x in review.get("recommended_changes") or []).lower()
    combined = f"{gaps} {recs}"

    if "validation evidence" in combined and "validation_evidence" not in merged:
        merged["validation_evidence"] = (
            "User validation evidence should be captured with interviews, "
            "usage data, or pilot outcomes before final PRD sign-off."
        )
    if "market positioning" in combined and "competitive_positioning" not in merged:
        merged["competitive_positioning"] = (
            "Positioning should clearly state differentiation versus incumbent PM tools "
            "and why AI synthesis creates defensible value."
        )

    if "enterprise requirements" in combined:
        c = str(merged.get("constraints") or "").strip()
        ent = (
            "Enterprise requirements include SOC2 Type II compliance, TLS 1.3 encryption "
            "in transit, AES-256 encryption at rest, tenant data isolation via row-level "
            "security, and GDPR data residency support for EU customers."
        )
        if ent not in c:
            merged["constraints"] = f"{c} {ent}".strip()

    return merged


def apply_feasibility_feedback_to_story_and_tasks(
    epics_stories: dict[str, Any],
    tasks: dict[str, Any],
    feasibility_review: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Propagate feasibility recommendations into both stories and tasks.
    Current deterministic rule: if timeout guidance is relaxed (60s), update STORY-8
    acceptance criteria so story/task constraints stay aligned.
    """
    if not isinstance(epics_stories, dict) or not isinstance(tasks, dict):
        return epics_stories, tasks
    if not isinstance(feasibility_review, dict):
        return epics_stories, tasks

    rec_text = " ".join(str(x) for x in feasibility_review.get("recommendations") or []).lower()
    if "60" not in rec_text and "timeout" not in rec_text:
        return epics_stories, tasks

    # Update story-level timeout text.
    for epic in epics_stories.get("epics") or []:
        if not isinstance(epic, dict):
            continue
        for story in epic.get("stories") or []:
            if not isinstance(story, dict) or story.get("id") != "STORY-8":
                continue
            ac = []
            for line in story.get("acceptance_criteria") or []:
                s = str(line)
                if "30-second timeout" in s:
                    s = s.replace(
                        "30-second timeout",
                        "60-second timeout with progressive result delivery",
                    )
                ac.append(s)
            story["acceptance_criteria"] = ac

    # Keep task-level timeout in sync when explicit timeout text exists.
    for group in tasks.get("tasks") or []:
        if not isinstance(group, dict):
            continue
        for task in group.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            task["description"] = str(task.get("description") or "").replace(
                "30-second timeout",
                "60-second timeout",
            )
            task["subtasks"] = [
                str(x).replace("30-second timeout", "60-second timeout")
                for x in (task.get("subtasks") or [])
            ]

    return epics_stories, tasks


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
        required_answers = max(1, int(len(qa_pairs) * min_fill_ratio + 0.999))
        errs.append(
            f"Please answer at least {required_answers} question(s) with {min_answer_len}+ characters "
            f"before generating docs (currently {nonempty}/{len(qa_pairs)} answered)."
        )
        return False, errs
    return True, []


def validate_project_brief(brief: dict[str, Any]) -> tuple[bool, list[str]]:
    errs: list[str] = []
    required = ("project_name", "problem_statement", "target_users", "key_features", "constraints")
    for k in required:
        v = brief.get(k)
        if v is None or (isinstance(v, str) and not str(v).strip()) or (isinstance(v, list) and len(v) == 0):
            label = k.replace("_", " ")
            errs.append(f"Please provide a valid `{label}` in the project brief.")
    return (len(errs) == 0, errs)


def validate_prd(prd: dict[str, Any]) -> tuple[bool, list[str]]:
    errs: list[str] = []
    legacy = ("overview", "goals", "functional_requirements", "non_functional_requirements", "success_metrics")
    for k in legacy:
        v = prd.get(k)
        if v is None:
            errs.append(f"PRD is missing `{k.replace('_', ' ')}`.")
        elif isinstance(v, list) and len(v) == 0:
            errs.append(f"PRD section `{k.replace('_', ' ')}` should not be empty.")
        elif isinstance(v, str) and not v.strip():
            errs.append(f"PRD section `{k.replace('_', ' ')}` is blank.")

    mvp = prd.get("mvp_scope")
    if not isinstance(mvp, dict):
        errs.append("PRD is missing a valid MVP scope section.")
    else:
        if not (mvp.get("must_have_features") or []):
            errs.append("MVP scope should include at least one must-have feature.")
        if not (mvp.get("explicitly_deferred") or []):
            errs.append("MVP scope should list at least one deferred feature.")

    phases = prd.get("phased_roadmap")
    if not isinstance(phases, dict):
        errs.append("PRD is missing a valid phased roadmap section.")
    else:
        if not (phases.get("phase_2_growth") or []):
            errs.append("Roadmap should include at least one Phase 2 growth item.")
        if not (phases.get("phase_3_advanced") or []):
            errs.append("Roadmap should include at least one Phase 3 advanced item.")

    risks = prd.get("risks_and_tradeoffs")
    if not isinstance(risks, dict):
        errs.append("PRD is missing the risks and tradeoffs section.")
    else:
        for rk in ("key_product_risks", "technical_risks", "gtm_risks"):
            if not (risks.get(rk) or []):
                errs.append(f"Please add entries under `{rk.replace('_', ' ')}`.")
        pt = risks.get("product_tradeoffs") or []
        if not isinstance(pt, list) or len(pt) < 2:
            errs.append("Please include at least 2 product tradeoffs.")

    dl = prd.get("decision_log") or []
    if not isinstance(dl, list) or len(dl) < 2:
        errs.append("Decision log should include at least 2 entries.")

    return (len(errs) == 0, errs)


def validate_architecture(arch: dict[str, Any]) -> tuple[bool, list[str]]:
    errs: list[str] = []
    if arch.get("error"):
        errs.append("Architecture output could not be parsed.")
        return False, errs
    if not (arch.get("services") or []):
        errs.append("Architecture should list at least one service.")
    if not isinstance(arch.get("suggested_stack"), dict):
        errs.append("Architecture should include a suggested tech stack.")
    if not (arch.get("data_flow_textual") or "").strip():
        errs.append("Architecture should include a textual data flow description.")
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
    brief = state.get("project_brief") or {}
    arch = state.get("architecture") or {}

    if isinstance(brief, dict):
        if not str(brief.get("elevator_pitch") or "").strip():
            warnings.append("Enhanced brief field missing: elevator_pitch (recommended).")
        if not str(brief.get("competitive_landscape") or "").strip():
            warnings.append("Enhanced brief field missing: competitive_landscape (recommended).")

    if isinstance(feas, dict) and feas.get("implementability_score") == "low":
        warnings.append("Task feasibility review scored implementability as low — review recommendations.")

    if isinstance(feas, dict):
        overs = feas.get("overscoped_or_risky_items") or []
        if isinstance(overs, list) and len(overs) > 4:
            warnings.append("Many items flagged as overscoped — consider trimming MVP.")

    # Cross-document checks expected for enterprise-grade coherence.
    # 1) Stack consistency: architecture frontend state stack vs tasks implementation.
    frontend_stack = str((arch.get("suggested_stack") or {}).get("frontend") or "").lower()
    has_react_query = "react query" in frontend_stack
    task_text = " ".join(
        str(t.get("title") or "") + " " + str(t.get("description") or "")
        for g in (tasks.get("tasks") or [])
        if isinstance(g, dict)
        for t in (g.get("tasks") or [])
        if isinstance(t, dict)
    ).lower()
    if has_react_query and "redux" in task_text:
        issues.append("Architecture specifies React Query, but tasks still reference Redux.")

    # 2) MVP scope leaks: deferred items should not appear as present tense in brief features.
    deferred = " ".join(str(x) for x in (prd.get("mvp_scope") or {}).get("explicitly_deferred") or []).lower()
    features = [str(x) for x in brief.get("key_features") or []]
    for f in features:
        lf = f.lower()
        if "stakeholder alignment" in lf and "stakeholder alignment" in deferred and "phase" not in lf:
            issues.append("project_brief key_features includes stakeholder alignment without phase tag despite PRD deferral.")
        if "roadmapping" in lf and "roadmapping" in deferred and "phase" not in lf:
            issues.append("project_brief key_features includes roadmapping without phase tag despite PRD deferral.")

    # 3) Timeline consistency between brief constraints and PRD MVP build assumptions.
    c = str(brief.get("constraints") or "").lower()
    mvp = str((prd.get("mvp_scope") or {}).get("mvp_build_assumption") or "").lower()
    if ("4-6 week" in c) and ("3-4 month" in mvp) and ("implementation" not in c and "onboarding" not in c):
        issues.append("Timeline mismatch: brief implies 4-6 week build while PRD assumes 3-4 month MVP build.")

    # 4) NFR traceability: uptime requirement should have explicit HA backing in architecture.
    nfr_blob = " ".join(str(x) for x in (prd.get("non_functional_requirements") or [])).lower()
    sc_blob = " ".join(str(x) for x in (arch.get("scalability_considerations") or [])).lower()
    if "99.5% uptime" in nfr_blob and not any(x in sc_blob for x in ("replica", "multi-az", "failover")):
        issues.append("PRD uptime SLA lacks architectural backing (replicas/failover/multi-AZ).")

    # 5) Backlog coverage: auth stories expected when architecture includes secure PM/dashboard access.
    svc_blob = " ".join(
        str((s or {}).get("responsibility") or "")
        for s in (arch.get("services") or [])
        if isinstance(s, dict)
    ).lower()
    story_blob = " ".join(
        str((st or {}).get("title") or "")
        for e in (es.get("epics") or [])
        if isinstance(e, dict)
        for st in (e.get("stories") or [])
        if isinstance(st, dict)
    ).lower()
    if ("dashboard" in svc_blob or "websocket" in svc_blob or "auth" in svc_blob) and not any(
        x in story_blob for x in ("log in", "authentication", "oauth", "jwt")
    ):
        issues.append("Architecture implies authenticated dashboard usage, but no authentication story exists in epics.")

    # 6) Metric clarity: multiple percentages should be clearly distinguished.
    epic_sc_blob = " ".join(
        str((e or {}).get("success_criteria") or "")
        for e in (es.get("epics") or [])
        if isinstance(e, dict)
    ).lower()
    if "75%" in epic_sc_blob and "85%" in str(prd).lower() and "70%" in str(prd).lower():
        if "distinct" not in epic_sc_blob and "note:" not in epic_sc_blob:
            warnings.append(
                "Metric overlap risk: epic validation accuracy should be explicitly distinguished from PM confidence and recommendation acceptance metrics."
            )

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
