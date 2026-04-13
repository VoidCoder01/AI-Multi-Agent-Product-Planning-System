import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export type AgentNodeState = "idle" | "active" | "completed";

export interface AgentNodeProps {
  label: string;
  icon: LucideIcon;
  state: AgentNodeState;
  index: number;
}

export function AgentNode({ label, icon: Icon, state, index }: AgentNodeProps) {
  const isActive = state === "active";
  const isDone = state === "completed";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1], delay: index * 0.05 }}
      className="flex min-w-[72px] flex-col items-center gap-2 sm:min-w-[88px]"
    >
      <div className="relative">
        <motion.div
          className={cn(
            "relative flex h-11 w-11 items-center justify-center rounded-xl border transition-all duration-300 ease-out sm:h-12 sm:w-12",
            isActive &&
              "border-primary/45 bg-primary/12 text-primary shadow-[0_0_0_1px_hsla(160,72%,45%,0.18)]",
            isDone && "border-emerald-500/32 bg-emerald-500/[0.09] text-emerald-400/90",
            !isActive && !isDone && "border-white/[0.09] bg-white/[0.03] text-muted-foreground/75",
          )}
        >
          {isDone ? (
            <motion.span
              initial={{ scale: 0.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 420, damping: 26 }}
              className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/22 text-emerald-400"
            >
              <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
            </motion.span>
          ) : (
            <Icon
              className={cn(
                "h-[18px] w-[18px] sm:h-5 sm:w-5",
                isActive && "drop-shadow-[0_0_6px_hsla(160,72%,45%,0.35)]",
              )}
            />
          )}
          {isActive && (
            <motion.span
              className="pointer-events-none absolute inset-0 rounded-xl border border-primary/35"
              animate={{ opacity: [0.35, 0.7, 0.35], scale: [1, 1.015, 1] }}
              transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
            />
          )}
        </motion.div>
      </div>
      <span
        className={cn(
          "text-center text-[10px] font-medium uppercase tracking-[0.14em] transition-colors duration-300",
          isActive && "text-primary",
          isDone && "text-emerald-400/85",
          !isActive && !isDone && "text-muted-foreground/60",
        )}
      >
        {label}
      </span>
    </motion.div>
  );
}
