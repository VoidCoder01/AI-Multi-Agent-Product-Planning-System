import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface LiveResultsPanelProps {
  streamingText: string;
  currentStage: string;
  partialResults: Record<string, unknown>;
}

const STAGE_LABELS: Record<string, { label: string; icon: string }> = {
  clarify:              { label: "Clarification Agent",    icon: "🔍" },
  validate_qa:          { label: "Validating Q&A",         icon: "🔍" },
  requirement:          { label: "Requirement Agent",      icon: "📋" },
  validate_brief:       { label: "Validating Brief",       icon: "📋" },
  pm:                   { label: "Product Manager",        icon: "🎯" },
  validate_prd:         { label: "Validating PRD",         icon: "🎯" },
  architect:            { label: "Architect Agent",        icon: "🏗️" },
  validate_architecture:{ label: "Validating Architecture",icon: "🏗️" },
  scrum:                { label: "Scrum Master",           icon: "📊" },
  task:                 { label: "Tech Lead",              icon: "⚒️" },
  final_validation:     { label: "Final Validation",       icon: "✅" },
  evaluate:             { label: "Quality Evaluation",     icon: "📈" },
  retry_requirement:    { label: "Retrying Brief",         icon: "🔄" },
  retry_pm:             { label: "Retrying PRD",           icon: "🔄" },
};

const ARTIFACT_LABELS: Record<string, string> = {
  project_brief:     "📋 Project Brief",
  prd:               "📄 PRD",
  architecture:      "🏗️ Architecture",
  epics_stories:     "📊 Epics & Stories",
  tasks:             "⚒️ Tasks",
  pm_brief_review:   "🎯 PM Review",
  scrum_prd_review:  "📊 Scrum Review",
  task_feasibility:  "✅ Feasibility",
  final_validation:  "✅ Validation",
  evaluation_scores: "📈 Scores",
};

function getPreview(value: unknown): string {
  const s = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  const clean = s.replace(/[{}"[\]]/g, " ").replace(/\s+/g, " ").trim();
  return clean.length > 160 ? clean.slice(0, 157) + "…" : clean;
}

export function LiveResultsPanel({ streamingText, currentStage, partialResults }: LiveResultsPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [streamingText]);

  const stageInfo = STAGE_LABELS[currentStage] ?? { label: currentStage, icon: "⚙️" };
  const completedArtifacts = Object.entries(partialResults).filter(
    ([k, v]) => ARTIFACT_LABELS[k] && v !== null && v !== undefined,
  );

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-white/[0.09] bg-card/38 p-4 backdrop-blur-xl">
      {/* Live streaming panel */}
      <div className="rounded-xl border border-primary/20 bg-black/30 overflow-hidden">
        <div className="flex items-center gap-2 border-b border-white/[0.06] px-3 py-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/60 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
          </span>
          {currentStage ? (
            <span className="text-[11px] font-medium text-primary/90">
              {stageInfo.icon} {stageInfo.label} — generating
            </span>
          ) : (
            <span className="text-[11px] font-medium text-muted-foreground/60">
              Waiting for next agent…
            </span>
          )}
        </div>
        <div
          ref={scrollRef}
          className="min-h-[120px] max-h-[220px] overflow-y-auto px-4 py-3 font-mono text-[11px] leading-relaxed text-[#E5E7EB]/75 whitespace-pre-wrap"
        >
          {streamingText || (
            <span className="text-muted-foreground/30 italic">Output will appear here as the agent generates…</span>
          )}
          {streamingText && (
            <span className="inline-block w-1.5 h-3.5 bg-primary/70 animate-pulse ml-0.5 align-middle" />
          )}
        </div>
      </div>

      {/* Completed artifacts */}
      {completedArtifacts.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/50">
            Completed artifacts
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            <AnimatePresence initial={false}>
              {completedArtifacts.map(([key, value]) => (
                <motion.div
                  key={key}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-3 py-2.5"
                >
                  <div className="flex items-center gap-1.5">
                    <span className="text-emerald-400/80 text-[11px]">✓</span>
                    <span className="text-[11px] font-semibold text-emerald-400/90">
                      {ARTIFACT_LABELS[key] ?? key}
                    </span>
                  </div>
                  <p className="mt-1 text-[10px] text-muted-foreground/60 leading-relaxed line-clamp-2">
                    {getPreview(value)}
                  </p>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}
    </div>
  );
}
