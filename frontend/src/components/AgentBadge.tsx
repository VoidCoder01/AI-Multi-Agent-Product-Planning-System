import { cn } from "@/lib/utils";
import { Bot, Brain, ClipboardList, Code, Search, Zap, Cpu, ShieldCheck } from "lucide-react";

const agentConfig: Record<string, { icon: typeof Bot; label: string; color: string }> = {
  master: { icon: Zap, label: "ORCHESTRATOR", color: "text-primary" },
  clarification: { icon: Search, label: "CLARIFIER", color: "text-accent" },
  requirement: { icon: Brain, label: "ANALYST", color: "text-primary" },
  pm: { icon: ClipboardList, label: "PM AGENT", color: "text-accent" },
  architect: { icon: Cpu, label: "ARCHITECT", color: "text-primary" },
  scrum: { icon: Code, label: "SCRUM AGENT", color: "text-accent" },
  task: { icon: Bot, label: "TASK AGENT", color: "text-primary" },
  evaluator: { icon: ShieldCheck, label: "EVALUATOR", color: "text-accent" },
};

interface AgentBadgeProps {
  agent: string;
  className?: string;
  /** Pulse dot — use only for live / running contexts */
  pulse?: boolean;
}

export function AgentBadge({ agent, className, pulse = true }: AgentBadgeProps) {
  const config = agentConfig[agent] || agentConfig.master;
  const Icon = config.icon;

  return (
    <div className={cn("inline-flex items-center gap-1.5 font-mono text-[10px] tracking-widest uppercase", config.color, className)}>
      <Icon className="w-3 h-3" />
      <span>{config.label}</span>
      {pulse && <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse-glow" />}
    </div>
  );
}
