import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown, Clock, PanelRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

export interface ExecutionLogEntry {
  id: string;
  agent: string;
  message: string;
  status: "running" | "completed";
  at: number;
  durationMs?: number;
  /** Legacy single detail blob */
  detail?: string;
  /** Truncated input description */
  inputSummary?: string;
  /** Short output description */
  outputSummary?: string;
}

export interface TraceRunningState {
  agent: string;
  message: string;
  inputSummary?: string;
}

interface LogPanelProps {
  entries: ExecutionLogEntry[];
  running?: TraceRunningState | null;
  defaultOpen?: boolean;
  className?: string;
}

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDuration(ms?: number) {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function LogPanel({ entries, running, defaultOpen = true, className }: LogPanelProps) {
  const sorted = useMemo(() => [...entries].sort((a, b) => b.at - a.at), [entries]);

  return (
    <motion.aside
      initial={false}
      animate={{ width: "100%" }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        "relative flex min-h-0 w-full shrink-0 flex-col overflow-hidden rounded-xl border border-white/[0.09] bg-card/35 shadow-[0_6px_28px_-10px_rgba(0,0,0,0.45)] backdrop-blur-xl",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2 border-b border-white/[0.06] px-3 py-2.5">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <PanelRight className="h-4 w-4 shrink-0 text-primary" />
          <span className="truncate text-[13px] font-semibold tracking-tight text-[#E5E7EB]">
            Execution trace
          </span>
        </div>
      </div>
      <div className="flex min-h-0 flex-1 flex-col">
        <ScrollArea className="h-full px-2 py-2">
          <div className="space-y-2 pr-2">
            {running && <RunningRow running={running} />}

            {sorted.map((entry) => (
              <LogRow key={entry.id} entry={entry} />
            ))}

            {!running && sorted.length === 0 && (
              <p className="px-2 py-8 text-center text-[12px] text-muted-foreground/95">
                Trace updates appear as agents run.
              </p>
            )}
          </div>
        </ScrollArea>
      </div>
    </motion.aside>
  );
}

function RunningRow({ running }: { running: TraceRunningState }) {
  const [expanded, setExpanded] = useState(false);
  const hasExtra = !!running.inputSummary;

  const body = (
    <>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-primary">
            {running.agent}
          </p>
          <p className="mt-1 text-[12px] leading-snug text-[#E5E7EB]/90">{running.message}</p>
        </div>
        <span className="flex w-[86px] shrink-0 items-center justify-end gap-1 text-[10px] text-muted-foreground">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/45 opacity-50" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
          </span>
          running
        </span>
      </div>
      {hasExtra && (
        <>
          <CollapsibleTrigger className="mt-2 flex w-full items-center justify-between text-[11px] text-primary/90 transition-colors hover:text-primary">
            <span>{expanded ? "Hide context" : "Input & context"}</span>
            <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")} />
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 space-y-2 rounded-md border border-white/[0.06] bg-black/25 px-2.5 py-2 text-[11px] leading-relaxed">
            {running.inputSummary && (
              <p>
                <span className="font-medium text-muted-foreground/95">Input: </span>
                <span className="text-[#E5E7EB]/88">{running.inputSummary}</span>
              </p>
            )}
          </CollapsibleContent>
        </>
      )}
    </>
  );

  if (!hasExtra) {
    return (
      <div className="rounded-lg border border-primary/22 bg-primary/[0.06] px-3 py-2.5 transition-colors duration-200">
        {body}
      </div>
    );
  }

  return (
    <Collapsible open={expanded} onOpenChange={setExpanded}>
      <div className="rounded-lg border border-primary/22 bg-primary/[0.06] px-3 py-2.5 transition-colors duration-200">
        {body}
      </div>
    </Collapsible>
  );
}

function LogRow({ entry }: { entry: ExecutionLogEntry }) {
  const [open, setOpen] = useState(false);
  const done = entry.status === "completed";
  const hasDetails = !!(entry.inputSummary || entry.outputSummary || entry.detail);
  const summaryLine = entry.outputSummary ?? entry.message;

  const header = (
    <div className="flex items-start gap-2">
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-[#E5E7EB]/92">
          {entry.agent}
        </p>
        <p className="mt-0.5 text-[12px] leading-snug text-[#E5E7EB]/82">{summaryLine}</p>
      </div>
      <div className="flex w-[86px] shrink-0 flex-col items-end gap-1 text-[10px] text-muted-foreground/95">
        <span className="flex w-full items-center justify-end gap-1 tabular-nums">
          <Clock className="h-3 w-3 opacity-80" />
          {formatTime(entry.at)}
        </span>
        {done && entry.durationMs != null && (
          <span className="w-full text-right text-emerald-400/95">{formatDuration(entry.durationMs)}</span>
        )}
        {hasDetails && (
          <ChevronDown
            className={cn("mt-0.5 h-3.5 w-3.5 self-end opacity-60 transition-transform", open && "rotate-180")}
          />
        )}
      </div>
    </div>
  );

  const details = (
    <div className="mt-3 space-y-2 border-t border-white/[0.06] pt-3 text-[11px] leading-relaxed">
      {entry.inputSummary && (
        <p>
          <span className="font-medium text-muted-foreground/95">Input: </span>
          <span className="text-[#E5E7EB]/88">{entry.inputSummary}</span>
        </p>
      )}
      {entry.outputSummary && (
        <p>
          <span className="font-medium text-muted-foreground/95">Output: </span>
          <span className="text-[#E5E7EB]/88">{entry.outputSummary}</span>
        </p>
      )}
      <p>
        <span className="font-medium text-muted-foreground/95">Time: </span>
        <span className="tabular-nums text-[#E5E7EB]/88">{formatDuration(entry.durationMs)}</span>
      </p>
      <p>
        <span className="font-medium text-muted-foreground/95">Status: </span>
        <span className={done ? "text-emerald-400/95" : "text-primary"}>
          {done ? "Completed" : "Running"}
        </span>
      </p>
      {entry.detail && (
        <p className="rounded-md bg-black/25 px-2 py-2 font-mono text-[10px] text-muted-foreground/95">
          {entry.detail}
        </p>
      )}
    </div>
  );

  const shell = "rounded-lg border px-3 py-2.5 transition-all duration-200";

  if (!hasDetails) {
    return (
      <div
        className={cn(
          shell,
          done
            ? "border-white/[0.08] bg-white/[0.035]"
            : "border-primary/18 bg-primary/[0.05]",
        )}
      >
        {header}
      </div>
    );
  }

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <div
        className={cn(
          shell,
          "hover:border-white/[0.12]",
          done ? "border-white/[0.08] bg-white/[0.035]" : "border-primary/18 bg-primary/[0.05]",
        )}
      >
        <CollapsibleTrigger className="flex w-full cursor-pointer text-left">{header}</CollapsibleTrigger>
        <CollapsibleContent>{details}</CollapsibleContent>
      </div>
    </Collapsible>
  );
}
