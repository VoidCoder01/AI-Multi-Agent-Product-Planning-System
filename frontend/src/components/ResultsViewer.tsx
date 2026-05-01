import JSZip from "jszip";
import { Download } from "lucide-react";
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
  { key: "project_brief",     label: "Project Brief",          agent: "requirement", filename: "project_brief.md" },
  { key: "pm_brief_review",   label: "PM ↔ Brief review",      agent: "pm",          filename: "pm_brief_review.md" },
  { key: "prd",               label: "PRD",                    agent: "pm",          filename: "prd.md" },
  { key: "architecture",      label: "Technical Architecture", agent: "architect",   filename: "architecture.md" },
  { key: "scrum_prd_review",  label: "Scrum ↔ PRD review",     agent: "scrum",       filename: "scrum_prd_review.md" },
  { key: "epics_stories",     label: "Epics & Stories",        agent: "scrum",       filename: "epics_stories.md" },
  { key: "task_feasibility",  label: "Feasibility review",     agent: "task",        filename: "task_feasibility.md" },
  { key: "tasks",             label: "Tasks",                  agent: "task",        filename: "tasks.md" },
  { key: "final_validation",  label: "Quality checks",         agent: "master",      filename: "final_validation.md" },
];

const INTERNAL_KEYS = new Set([
  "session_id", "error", "halt_reason", "validation_errors",
  "rag_context", "questions", "langgraph_thread_id",
]);

function getContentString(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function getDescription(value: unknown): string {
  const s = getContentString(value);
  const oneLine = s.replace(/\s+/g, " ").trim();
  return oneLine.length <= 190 ? oneLine : `${oneLine.slice(0, 187)}…`;
}

function toMarkdown(label: string, value: unknown): string {
  return `# ${label}\n\n\`\`\`json\n${getContentString(value)}\n\`\`\`\n`;
}

function downloadFile(filename: string, content: string, mime = "text/markdown;charset=utf-8") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function downloadZip(results: Record<string, unknown>, sections: typeof docSections) {
  const zip = new JSZip();
  const folder = zip.folder("project-docs")!;
  for (const s of sections) {
    const val = results[s.key];
    if (val !== null && val !== undefined) {
      folder.file(s.filename, toMarkdown(s.label, val));
    }
  }
  folder.file("full_output.json", JSON.stringify(results, null, 2));
  const blob = await zip.generateAsync({ type: "blob" });
  downloadFile("project-docs.zip", "", "application/zip");
  // override the blob directly
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "project-docs.zip";
  a.click();
  URL.revokeObjectURL(url);
}

export function ResultsViewer({ results }: ResultsViewerProps) {
  const visibleResults = Object.fromEntries(
    Object.entries(results).filter(([k, v]) => !INTERNAL_KEYS.has(k) && v !== null && v !== undefined),
  );
  const availableSections = docSections.filter((s) => visibleResults[s.key] !== undefined);

  const sections =
    availableSections.length > 0
      ? availableSections
      : Object.keys(visibleResults).map((key) => ({
          key,
          label: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
          agent: "master",
          filename: `${key}.md`,
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
      {/* Header + download bar */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold tracking-tight text-[#E5E7EB]">Generated Artifacts</h3>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground/90">
            Expand sections below. Download individual files or everything as a ZIP.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => downloadFile("full_output.json", JSON.stringify(results, null, 2), "application/json")}
            className="flex items-center gap-1.5 rounded-lg border border-white/[0.1] bg-white/[0.04] px-3 py-1.5 text-[11px] font-medium text-muted-foreground hover:bg-white/[0.08] hover:text-foreground transition-colors"
          >
            <Download className="h-3 w-3" /> JSON
          </button>
          <button
            onClick={() => downloadZip(visibleResults, sections as typeof docSections)}
            className="flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-3 py-1.5 text-[11px] font-medium text-primary hover:bg-primary/20 transition-colors"
          >
            <Download className="h-3 w-3" /> Download all (.zip)
          </button>
        </div>
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
                <p className="text-base font-semibold text-[#E5E7EB]">{group.title}</p>
                <p className="mt-1 text-[13px] font-normal text-muted-foreground/85">
                  {group.subtitle} ({group.sections.length})
                </p>
              </div>
            </AccordionTrigger>
            <AccordionContent className="pb-5">
              <div className="grid gap-4 sm:grid-cols-2">
                {group.sections.map((section, i) => (
                  <div key={section.key} className="group relative">
                    <ArtifactCard
                      title={section.label}
                      description={getDescription(visibleResults[section.key])}
                      agentKey={section.agent}
                      content={getContentString(visibleResults[section.key])}
                      index={groupIdx * 10 + i}
                    />
                    <button
                      onClick={() =>
                        downloadFile(
                          section.filename,
                          toMarkdown(section.label, visibleResults[section.key]),
                        )
                      }
                      className="absolute right-3 top-3 hidden group-hover:flex items-center gap-1 rounded-md bg-black/50 px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                      title={`Download ${section.label}`}
                    >
                      <Download className="h-2.5 w-2.5" /> .md
                    </button>
                  </div>
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
                  <div key={section.key} className="group relative">
                    <ArtifactCard
                      title={section.label}
                      description={getDescription(visibleResults[section.key])}
                      agentKey={section.agent}
                      content={getContentString(visibleResults[section.key])}
                      index={80 + i}
                    />
                    <button
                      onClick={() =>
                        downloadFile(
                          section.filename,
                          toMarkdown(section.label, visibleResults[section.key]),
                        )
                      }
                      className="absolute right-3 top-3 hidden group-hover:flex items-center gap-1 rounded-md bg-black/50 px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <Download className="h-2.5 w-2.5" /> .md
                    </button>
                  </div>
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        )}
      </Accordion>
    </div>
  );
}
