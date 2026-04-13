import { motion } from "framer-motion";
import { Layers, Radio } from "lucide-react";

export function TerminalHeader() {
  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="relative z-20 w-full border-b border-white/[0.08] bg-[hsla(222,28%,7%,0.72)] shadow-sm backdrop-blur-2xl"
    >
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-10">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/[0.1] bg-white/[0.04] shadow-[0_0_0_1px_hsla(160,72%,45%,0.12)]">
            <Layers className="h-[18px] w-[18px] text-primary" />
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-[15px] font-semibold tracking-tight text-[#E5E7EB]">
              NexPlan<span className="text-primary">.AI</span>
            </h1>
            <p className="truncate text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Multi-agent product planning
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 sm:gap-5">
          <div className="hidden items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 sm:flex">
            <Radio className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
              5 agents live
            </span>
          </div>
          <div className="flex gap-1.5 opacity-80">
            <span className="h-2 w-2 rounded-full bg-rose-500/70" />
            <span className="h-2 w-2 rounded-full bg-amber-400/70" />
            <span className="h-2 w-2 rounded-full bg-primary/80" />
          </div>
        </div>
      </div>
    </motion.header>
  );
}
