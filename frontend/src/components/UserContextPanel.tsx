import { motion } from "framer-motion";
import { ClipboardList } from "lucide-react";
import { cn } from "@/lib/utils";

function truncate(s: string, max: number) {
  const t = s.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

interface UserContextPanelProps {
  productIdea: string;
  questions: string[];
  answers: Record<string, string>;
  className?: string;
}

export function UserContextPanel({ productIdea, questions, answers, className }: UserContextPanelProps) {
  const idea = productIdea.trim();
  const pairs = questions
    .map((q, i) => ({
      q,
      a: answers[`q${i + 1}`]?.trim() ?? "",
    }))
    .filter((p) => p.a.length > 0);

  if (!idea && pairs.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        "rounded-xl border border-white/[0.09] bg-white/[0.03] px-4 py-4 text-[13px] backdrop-blur-sm sm:px-5",
        className,
      )}
    >
      <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#E5E7EB]/70">
        <ClipboardList className="h-3.5 w-3.5 text-primary/90" />
        Your context
      </div>
      {idea && (
        <div className="mb-4">
          <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/95">
            Product idea
          </p>
          <p className="leading-relaxed text-[#E5E7EB]/95">{truncate(idea, 280)}</p>
        </div>
      )}
      {pairs.length > 0 && (
        <div>
          <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/95">
            Captured answers
          </p>
          <ul className="space-y-2.5">
            {pairs.map((p, i) => (
              <li
                key={i}
                className="rounded-lg border border-white/[0.06] bg-black/15 px-3 py-2 text-[12px] leading-snug"
              >
                <span className="text-muted-foreground/95">{truncate(p.q, 100)}</span>
                <span className="mt-1 block text-[#E5E7EB]/90">{truncate(p.a, 160)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </motion.div>
  );
}
