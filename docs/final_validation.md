# Quality Checks

```json
{
  "passed": false,
  "issues": [
    "timeline_consistency: project_brief constraints and PRD MVP timeline were misaligned before feedback normalization",
    "stack_consistency: TASK-34 previously referenced Redux while architecture mandates React Query",
    "mvp_scope_consistency: stakeholder alignment and roadmapping were listed as current features but deferred in PRD",
    "security_coverage: authentication story missing from backlog while architecture requires secure PM access",
    "nfr_architecture_traceability: 99.5% uptime SLA required explicit HA/replica/multi-AZ design in architecture",
    "review_feedback_propagation: feasibility timeout recommendation must be reflected in both stories and tasks"
  ],
  "warnings": [
    "MVP still has integration complexity risks; monitor Confluence ingestion and partner API reliability.",
    "Validate confidence scoring calibration against real production outcomes during pilot rollout."
  ]
}
```
