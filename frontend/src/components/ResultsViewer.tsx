import { ArtifactCard } from "@/components/ArtifactCard";

interface ResultsViewerProps {
  results: Record<string, unknown>;
}

const docSections = [
  { key: "project_brief", label: "Project Brief", agent: "requirement" },
  { key: "pm_brief_review", label: "PM ↔ Brief review", agent: "pm" },
  { key: "prd", label: "PRD", agent: "pm" },
  { key: "architecture", label: "Technical architecture", agent: "master" },
  { key: "scrum_prd_review", label: "Scrum ↔ PRD review", agent: "scrum" },
  { key: "epics_stories", label: "Epics & Stories", agent: "scrum" },
  { key: "task_feasibility", label: "Feasibility review", agent: "task" },
  { key: "tasks", label: "Tasks", agent: "task" },
  { key: "final_validation", label: "Quality checks", agent: "master" },
];

function getContentString(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function getDescription(value: unknown): string {
  const s = getContentString(value);
  const oneLine = s.replace(/\s+/g, " ").trim();
  if (oneLine.length <= 140) return oneLine;
  return `${oneLine.slice(0, 137)}…`;
}

export function ResultsViewer({ results }: ResultsViewerProps) {
  const availableSections = docSections.filter((s) => results[s.key] !== undefined);

  const sections =
    availableSections.length > 0
      ? availableSections
      : Object.keys(results).map((key) => ({
          key,
          label: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
          agent: "master",
        }));

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {sections.map((section, i) => (
        <ArtifactCard
          key={section.key}
          title={section.label}
          description={getDescription(results[section.key])}
          agentKey={section.agent}
          content={getContentString(results[section.key])}
          index={i}
        />
      ))}
    </div>
  );
}
