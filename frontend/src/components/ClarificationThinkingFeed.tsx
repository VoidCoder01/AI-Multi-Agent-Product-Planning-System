import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

const REASONING_STEPS: { prefix: "check" | "arrow"; text: string }[] = [
  { prefix: "check", text: "Identifying target users and core problem…" },
  { prefix: "check", text: "Scanning for missing inputs (pricing, scope, constraints)…" },
  { prefix: "check", text: "Analyzing feature scope and success signals…" },
  { prefix: "check", text: "Mapping your idea to clarification dimensions…" },
  { prefix: "arrow", text: "Generating tailored clarification questions…" },
];

const STEP_DELAY_MS = 520;

interface ClarificationThinkingFeedProps {
  active: boolean;
  className?: string;
}

export function ClarificationThinkingFeed({ active, className }: ClarificationThinkingFeedProps) {
  const [visibleCount, setVisibleCount] = useState(0);

  useEffect(() => {
    if (!active) {
      setVisibleCount(0);
      return;
    }
    setVisibleCount(0);
    const timers: ReturnType<typeof setTimeout>[] = [];
    for (let i = 0; i < REASONING_STEPS.length; i++) {
      timers.push(
        window.setTimeout(() => {
          setVisibleCount(i + 1);
        }, i * STEP_DELAY_MS),
      );
    }
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [active]);

  return (
    <div
      className={cn(
        "rounded-2xl border border-white/[0.09] bg-card/35 px-5 py-5 backdrop-blur-xl sm:px-6",
        className,
      )}
    >
      <div className="mb-4 flex items-center gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#E5E7EB]/75">
          Live reasoning
        </span>
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/30 opacity-50" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-primary/90" />
        </span>
      </div>
      <ul className="space-y-2.5">
        <AnimatePresence initial={false}>
          {REASONING_STEPS.slice(0, visibleCount).map((step, i) => (
            <motion.li
              key={`${step.text}-${i}`}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
              className="flex gap-2.5 text-[13px] leading-snug text-[#E5E7EB]/92"
            >
              <span className="mt-0.5 shrink-0 font-medium text-primary/95" aria-hidden>
                {step.prefix === "check" ? "✔" : "→"}
              </span>
              <span>{step.text}</span>
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>
      {visibleCount > 0 && visibleCount < REASONING_STEPS.length && (
        <div className="mt-3 flex items-center gap-1 pl-7">
          {[0, 1, 2].map((d) => (
            <motion.span
              key={d}
              className="h-1 w-1 rounded-full bg-primary/70"
              animate={{ opacity: [0.35, 1, 0.35] }}
              transition={{ duration: 0.9, repeat: Infinity, delay: d * 0.12 }}
            />
          ))}
          <span className="ml-2 text-[11px] text-muted-foreground/90">Working…</span>
        </div>
      )}
    </div>
  );
}
