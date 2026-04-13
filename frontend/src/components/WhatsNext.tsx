import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface WhatsNextProps {
  step: number;
  loading: boolean;
  generatePhase: number;
  className?: string;
}

const PHASE_HINTS = [
  "Synthesizing a structured brief from your answers…",
  "Drafting requirements and success metrics…",
  "Breaking work into epics and user stories…",
  "Decomposing stories into engineering tasks…",
  "Finalizing artifacts for export…",
];

export function WhatsNext({ step, loading, generatePhase, className }: WhatsNextProps) {
  let text = "";
  if (step === 1 && !loading) {
    text = "Run the clarifier to produce questions aligned to your idea.";
  } else if (step === 1 && loading) {
    text = "Interpreting your idea and drafting clarification questions.";
  } else if (step === 2 && !loading) {
    text = "Answer each question, then generate full documentation.";
  } else if (step === 2 && loading) {
    text =
      generatePhase === 0
        ? "Generating requirement analysis based on your inputs."
        : PHASE_HINTS[Math.min(generatePhase, PHASE_HINTS.length - 1)] ?? PHASE_HINTS[0];
  } else if (step === 3) {
    text = "Review artifacts below or export JSON / Markdown.";
  }

  if (!text) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.25 }}
      className={cn(
        "flex items-start gap-2.5 rounded-lg border border-white/[0.07] bg-white/[0.025] px-4 py-3 text-[13px] leading-snug text-[#E5E7EB]/88",
        className,
      )}
    >
      <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-primary/85" aria-hidden />
      <div>
        <span className="font-semibold text-[#E5E7EB]/95">Next: </span>
        {text}
      </div>
    </motion.div>
  );
}
