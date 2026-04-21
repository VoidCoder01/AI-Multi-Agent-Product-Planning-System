import { ArtifactCard } from "@/components/ArtifactCard";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

interface ResultsViewerProps {
  results: Record<string, unknown>;
}

const docSections = [
  { key: "project_brief", label: "Project Brief", agent: "requirement" },
  { key: "pm_brief_review", label: "PM ↔ Brief review", agent: "pm" },
  { key: "prd", label: "PRD", agent: "pm" },
  { key: "architecture", label: "Technical Architecture", agent: "architect" },
  { key: "scrum_prd_review", label: "Scrum ↔ PRD review", agent: "scrum" },
  { key: "epics_stories", label: "Epics & Stories", agent: "scrum" },
  { key: "task_feasibility", label: "Feasibility review", agent: "task" },
  { key: "tasks", label: "Tasks", agent: "task" },
  { key: "final_validation", label: "Quality checks", agent: "master" },
];

/** Keys returned by the backend that are NOT displayable artifacts */
const INTERNAL_KEYS = new Set([
  "session_id", "error", "halt_reason", "validation_errors",
  "rag_context", "questions",
]);

function getContentString(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function getDescription(value: unknown): string {
  const s = getContentString(value);
  const oneLine = s.replace(/\s+/g, " ").trim();
  if (oneLine.length <= 190) return oneLine;
  return `${oneLine.slice(0, 187)}…`;
}

export function ResultsViewer({ results }: ResultsViewerProps) {
  const visibleResults = Object.fromEntries(
    Object.entries(results).filter(([k, v]) => !INTERNAL_KEYS.has(k) && v !== null && v !== undefined)
  );
  const availableSections = docSections.filter((s) => visibleResults[s.key] !== undefined);

  const sections =
    availableSections.length > 0
      ? availableSections
      : Object.keys(visibleResults).map((key) => ({
          key,
          label: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
          agent: "master",
        }));

  const groups = [
    {
      key: "core",
      title: "Core Planning Artifacts",
      subtitle: "Primary documents teams usually review first.",
      sectionKeys: ["project_brief", "prd", "architecture", "epics_stories", "tasks"],
      defaultOpen: true,
    },
    {
      key: "reviews",
      title: "Review & Feasibility Layers",
      subtitle: "Supporting assessments from PM, Scrum, and Tech Lead agents.",
      sectionKeys: ["pm_brief_review", "scrum_prd_review", "task_feasibility"],
      defaultOpen: false,
    },
    {
      key: "quality",
      title: "Quality & Validation",
      subtitle: "Final checks and consistency signals before export.",
      sectionKeys: ["final_validation"],
      defaultOpen: false,
    },
  ] as const;

  const grouped = groups
    .map((group) => ({
      ...group,
      sections: group.sectionKeys
        .map((k) => sections.find((s) => s.key === k))
        .filter((s): s is NonNullable<typeof s> => Boolean(s)),
    }))
    .filter((g) => g.sections.length > 0);

  const groupedKeys = new Set(grouped.flatMap((g) => g.sections.map((s) => s.key)));
  const otherSections = sections.filter((s) => !groupedKeys.has(s.key));

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-lg font-semibold tracking-tight text-[#E5E7EB]">
          Generated Artifacts
        </h3>
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground/90">
          Expand sections as needed. Core outputs stay prominent while supporting
          diagnostics remain one click away.
        </p>
      </div>

      <Accordion type="multiple" defaultValue={grouped.filter((g) => g.defaultOpen).map((g) => g.key)}>
        {grouped.map((group, groupIdx) => (
          <AccordionItem
            key={group.key}
            value={group.key}
            className="overflow-hidden rounded-2xl border border-white/[0.08] bg-white/[0.02] px-4 sm:px-5"
          >
            <AccordionTrigger className="py-4 hover:no-underline">
              <div className="text-left">
                <p className="text-base font-semibold text-[#E5E7EB]">
                  {group.title}
                </p>
                <p className="mt-1 text-[13px] font-normal text-muted-foreground/85">
                  {group.subtitle} ({group.sections.length})
                </p>
              </div>
            </AccordionTrigger>
            <AccordionContent className="pb-5">
              <div className="grid gap-4 sm:grid-cols-2">
                {group.sections.map((section, i) => (
                  <ArtifactCard
                    key={section.key}
                    title={section.label}
                    description={getDescription(visibleResults[section.key])}
                    agentKey={section.agent}
                    content={getContentString(visibleResults[section.key])}
                    index={groupIdx * 10 + i}
                  />
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        ))}

        {otherSections.length > 0 && (
          <AccordionItem
            value="other"
            className="overflow-hidden rounded-2xl border border-white/[0.08] bg-white/[0.02] px-4 sm:px-5"
          >
            <AccordionTrigger className="py-4 hover:no-underline">
              <div className="text-left">
                <p className="text-base font-semibold text-[#E5E7EB]">Additional Outputs</p>
                <p className="mt-1 text-[13px] font-normal text-muted-foreground/85">
                  Extra result keys returned by the pipeline ({otherSections.length})
                </p>
              </div>
            </AccordionTrigger>
            <AccordionContent className="pb-5">
              <div className="grid gap-4 sm:grid-cols-2">
                {otherSections.map((section, i) => (
                  <ArtifactCard
                    key={section.key}
                    title={section.label}
                    description={getDescription(visibleResults[section.key])}
                    agentKey={section.agent}
                    content={getContentString(visibleResults[section.key])}
                    index={80 + i}
                  />
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        )}
      </Accordion>
    </div>
  );
}
