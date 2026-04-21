import { useEffect, useRef, useState } from "react";
import { Search, Brain, ClipboardList, Code, Bot, Cpu, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { AgentNode, type AgentNodeState } from "@/components/AgentNode";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const agents = [
  {
    id: "clarification",
    icon: Search,
    label: "Clarifier",
    description: "Turns your idea into precise questions and resolves ambiguity before planning.",
  },
  {
    id: "requirement",
    icon: Brain,
    label: "Analyst",
    description: "Structures goals, users, and constraints into a coherent project brief.",
  },
  {
    id: "pm",
    icon: ClipboardList,
    label: "PM",
    description: "Reviews the brief, then produces the PRD: scope, requirements, metrics, and risks.",
  },
  {
    id: "architect",
    icon: Cpu,
    label: "Architect",
    description: "Designs the technical architecture: services, stack, data flow, and scalability.",
  },
  {
    id: "scrum",
    icon: Code,
    label: "Scrum",
    description: "Reviews the PRD, then breaks scope into epics and user stories with acceptance criteria.",
  },
  {
    id: "task",
    icon: Bot,
    label: "Tasks",
    description: "Validates feasibility, then decomposes stories into engineering tasks.",
  },
  {
    id: "validation",
    icon: ShieldCheck,
    label: "Validate",
    description: "Runs cross-document consistency checks across all generated artifacts.",
  },
] as const;

export interface PipelineFlowProps {
  states: AgentNodeState[];
}

function FlowConnector({
  leftDone,
  pulse,
  burstKey,
}: {
  leftDone: boolean;
  pulse: boolean;
  burstKey: number;
}) {
  return (
    <div
      className="relative mx-0.5 mb-7 h-px min-w-[16px] flex-1 sm:mx-1 sm:min-w-[24px] md:min-w-[36px]"
      aria-hidden
    >
      <div
        className={cn(
          "absolute inset-0 h-px rounded-full transition-colors duration-500",
          leftDone ? "bg-gradient-to-r from-emerald-500/40 to-primary/22" : "bg-white/[0.08]",
        )}
      />
      {pulse && (
        <div className="absolute inset-0 h-px overflow-hidden rounded-full opacity-90">
          <div
            key={burstKey}
            className="h-full w-[45%] animate-flow-shimmer bg-gradient-to-r from-transparent via-primary/75 to-transparent"
          />
        </div>
      )}
    </div>
  );
}

export function PipelineFlow({ states }: PipelineFlowProps) {
  const prevStates = useRef(states);
  const [burst, setBurst] = useState<Record<number, number>>({});

  useEffect(() => {
    states.forEach((s, i) => {
      if (s === "completed" && prevStates.current[i] !== "completed") {
        setBurst((b) => ({ ...b, [i]: (b[i] ?? 0) + 1 }));
      }
    });
    prevStates.current = states;
  }, [states]);

  return (
    <div className="flex w-full max-w-5xl flex-wrap items-start justify-center gap-y-5 px-2 py-6 sm:flex-nowrap sm:gap-y-0">
      {agents.map((agent, i) => {
        const state = states[i] ?? "idle";
        const Icon = agent.icon;
        const next = states[i + 1] ?? "idle";
        const leftDone = state === "completed";
        const pulse =
          state === "active" ||
          (leftDone && (next === "active" || next === "idle"));

        return (
          <div key={agent.id} className="flex flex-[0_0_auto] items-start">
            <Tooltip delayDuration={200}>
              <TooltipTrigger asChild>
                <div className="cursor-default">
                  <AgentNode label={agent.label} icon={Icon} state={state} index={i} />
                </div>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-[240px] border-white/[0.1] bg-[hsl(222,28%,10%)] px-3 py-2 text-[11px] leading-snug text-[#E5E7EB]/92 shadow-lg">
                <span className="font-semibold text-primary">{agent.label}</span>
                <p className="mt-1 text-muted-foreground/95">{agent.description}</p>
              </TooltipContent>
            </Tooltip>
            {i < agents.length - 1 && (
              <FlowConnector
                leftDone={leftDone}
                pulse={pulse}
                burstKey={burst[i] ?? 0}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
