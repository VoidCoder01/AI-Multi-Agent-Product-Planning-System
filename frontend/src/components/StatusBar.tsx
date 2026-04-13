import { motion } from "framer-motion";
import { Activity, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";

export type AppStage = "input" | "clarification" | "planning" | "output";

interface StatusBarProps {
  stage: AppStage;
  /** 0–100 */
  progress: number;
  agentsOnline?: number;
  /** e.g. "Clarification phase" */
  phaseName: string;
  /** Completed agents in the 5-step pipeline */
  completedAgents: number;
  totalAgents?: number;
  /** Compact step strip */
  miniSteps?: { key: string; label: string; state: "done" | "active" | "pending" }[];
  className?: string;
}

const stageLabel: Record<AppStage, string> = {
  input: "Input",
  clarification: "Clarification",
  planning: "Planning",
  output: "Output",
};

export function StatusBar({
  stage,
  progress,
  agentsOnline = 5,
  phaseName,
  completedAgents,
  totalAgents = 5,
  miniSteps,
  className,
}: StatusBarProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        "flex flex-col gap-4 rounded-xl border border-white/[0.09] bg-card/35 px-4 py-4 shadow-sm backdrop-blur-xl sm:flex-row sm:items-start sm:justify-between sm:gap-6",
        className,
      )}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-3 text-sm text-[#E5E7EB]/92">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.04]">
              <Cpu className="h-4 w-4 text-primary" />
            </span>
            <div className="leading-tight">
              <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground/95">
                System status
              </p>
              <p className="text-sm font-semibold tracking-tight">
                Stage: <span className="text-primary">{stageLabel[stage]}</span>
              </p>
            </div>
          </div>
          <div className="hidden h-8 w-px bg-white/[0.08] sm:block" />
          <div className="flex items-center gap-2 text-[13px]">
            <Activity className="h-4 w-4 text-emerald-400/90" />
            <span>
              Agents active:{" "}
              <span className="font-semibold tabular-nums text-[#E5E7EB]">{agentsOnline}</span>
            </span>
          </div>
        </div>
        <div className="space-y-1.5">
          <p className="text-[12px] font-medium leading-snug text-[#E5E7EB]/95">{phaseName}</p>
          <p className="text-[11px] text-muted-foreground/95">
            Agent progress:{" "}
            <span className="font-semibold tabular-nums text-[#E5E7EB]/90">
              {completedAgents} of {totalAgents}
            </span>{" "}
            completed
          </p>
          {miniSteps && miniSteps.length > 0 && (
            <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1 pt-1 text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground/90">
              {miniSteps.map((s, i) => (
                <span key={s.key} className="flex items-center gap-1.5">
                  {i > 0 && <span className="text-white/20">→</span>}
                  <span
                    className={cn(
                      s.state === "done" && "text-emerald-400/95",
                      s.state === "active" && "text-primary",
                      s.state === "pending" && "text-muted-foreground/55",
                    )}
                  >
                    {s.label}
                    {s.state === "done" && " ✔"}
                    {s.state === "active" && " ·"}
                    {s.state === "pending" && " ⏳"}
                  </span>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="w-full min-w-[200px] sm:max-w-sm">
        <div className="mb-2 flex items-center justify-between gap-2 text-[11px] text-muted-foreground/95">
          <span>Pipeline progress</span>
          <span className="tabular-nums text-[#E5E7EB]/88">{Math.round(progress)}%</span>
        </div>
        <Progress value={progress} className="h-2 bg-white/[0.07]" />
      </div>
    </motion.div>
  );
}
